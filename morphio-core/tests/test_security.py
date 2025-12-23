"""
Tests for security utilities.
"""

import pytest

from morphio_core.exceptions import SSRFBlockedError
from morphio_core.security import (
    Anonymizer,
    URLValidator,
    URLValidatorConfig,
    anonymize_content,
)


class TestAnonymizer:
    """Tests for the Anonymizer class."""

    def test_anonymize_email(self):
        """Test email anonymization."""
        anonymizer = Anonymizer()
        content = "Contact me at test@example.com for info."
        result = anonymizer.anonymize(content)

        assert "test@example.com" not in result
        assert "[EMAIL_1]" in result

    def test_anonymize_phone(self):
        """Test phone number anonymization."""
        anonymizer = Anonymizer()
        content = "Call me at 555-123-4567 or (555) 987-6543."
        result = anonymizer.anonymize(content)

        assert "555-123-4567" not in result
        assert "(555) 987-6543" not in result
        assert "[PHONE_1]" in result
        assert "[PHONE_2]" in result

    def test_anonymize_ssn(self):
        """Test SSN anonymization."""
        anonymizer = Anonymizer()
        content = "SSN: 123-45-6789"
        result = anonymizer.anonymize(content)

        assert "123-45-6789" not in result
        assert "[SSN_1]" in result

    def test_anonymize_ip(self):
        """Test IP address anonymization."""
        anonymizer = Anonymizer()
        content = "Server at 192.168.1.1 is down."
        result = anonymizer.anonymize(content)

        assert "192.168.1.1" not in result
        assert "[IP_ADDRESS_1]" in result

    def test_anonymize_valid_ips(self):
        """Test that valid IP addresses are anonymized."""
        anonymizer = Anonymizer()

        # Test various valid IPs
        valid_ips = [
            ("0.0.0.0", "minimum valid"),
            ("255.255.255.255", "maximum valid"),
            ("127.0.0.1", "loopback"),
            ("10.0.0.255", "private class A"),
            ("172.16.0.1", "private class B"),
        ]

        for ip, description in valid_ips:
            anonymizer = Anonymizer()
            content = f"Server: {ip}"
            result = anonymizer.anonymize(content)
            assert ip not in result, f"Failed to anonymize {description}: {ip}"
            assert "[IP_ADDRESS_1]" in result

    def test_anonymize_invalid_ips_unchanged(self):
        """Test that invalid IPs are NOT anonymized."""
        anonymizer = Anonymizer()

        invalid_ips = [
            "999.999.999.999",
            "256.256.256.256",
            "192.168.1.256",
            "300.168.1.1",
        ]

        for invalid_ip in invalid_ips:
            anonymizer = Anonymizer()
            content = f"Invalid IP: {invalid_ip}"
            result = anonymizer.anonymize(content)
            # Invalid IPs should remain unchanged
            assert invalid_ip in result, f"{invalid_ip} should not match IP pattern"
            assert "[IP_ADDRESS" not in result

    def test_deanonymize(self):
        """Test deanonymization restores original content."""
        anonymizer = Anonymizer()
        original = "Email: test@example.com, Phone: 555-123-4567"

        anonymized = anonymizer.anonymize(original)
        restored = anonymizer.deanonymize(anonymized)

        assert restored == original

    def test_anonymize_content_disabled(self):
        """Test anonymize_content with enabled=False."""
        content = "test@example.com"
        result = anonymize_content(content, enabled=False)
        assert result == content

    def test_anonymize_content_enabled(self):
        """Test anonymize_content with enabled=True."""
        content = "test@example.com"
        result = anonymize_content(content, enabled=True)
        assert "test@example.com" not in result
        assert "[EMAIL_1]" in result


class TestURLValidator:
    """Tests for the URLValidator class."""

    def test_public_url_allowed(self, fake_dns_resolver):
        """Test that public URLs are allowed."""
        resolver = fake_dns_resolver({"example.com": ["93.184.216.34"]})
        validator = URLValidator(resolve_func=resolver)

        assert not validator.is_blocked("https://example.com/path")

    def test_localhost_blocked(self, fake_dns_resolver):
        """Test that localhost is blocked."""
        resolver = fake_dns_resolver({"localhost": ["127.0.0.1"]})
        validator = URLValidator(resolve_func=resolver)

        assert validator.is_blocked("http://localhost/admin")

    def test_loopback_ip_blocked(self, fake_dns_resolver):
        """Test that loopback IPs are blocked."""
        resolver = fake_dns_resolver({"evil.com": ["127.0.0.1"]})
        validator = URLValidator(resolve_func=resolver)

        assert validator.is_blocked("http://evil.com/")

    def test_private_ip_blocked(self, fake_dns_resolver):
        """Test that private IPs are blocked."""
        resolver = fake_dns_resolver({"internal.corp": ["10.0.0.1"]})
        validator = URLValidator(resolve_func=resolver)

        assert validator.is_blocked("http://internal.corp/")

    def test_link_local_blocked(self, fake_dns_resolver):
        """Test that link-local addresses are blocked (metadata service)."""
        resolver = fake_dns_resolver({"metadata": ["169.254.169.254"]})
        validator = URLValidator(resolve_func=resolver)

        assert validator.is_blocked("http://metadata/latest/")

    def test_invalid_scheme_blocked(self, fake_dns_resolver):
        """Test that non-http(s) schemes are blocked."""
        resolver = fake_dns_resolver({"example.com": ["93.184.216.34"]})
        validator = URLValidator(resolve_func=resolver)

        assert validator.is_blocked("ftp://example.com/file")
        assert validator.is_blocked("file:///etc/passwd")

    def test_dns_failure_blocked(self, fake_dns_resolver):
        """Test that DNS resolution failures are blocked."""
        resolver = fake_dns_resolver({})  # No DNS entries
        validator = URLValidator(resolve_func=resolver)

        assert validator.is_blocked("http://nonexistent.invalid/")

    def test_custom_allowed_cidr(self, fake_dns_resolver):
        """Test that custom allowed CIDRs override blocks."""
        resolver = fake_dns_resolver({"internal": ["10.0.0.5"]})
        config = URLValidatorConfig(custom_allowed_cidrs=["10.0.0.0/24"])
        validator = URLValidator(config, resolve_func=resolver)

        assert not validator.is_blocked("http://internal/")

    def test_custom_blocked_cidr(self, fake_dns_resolver):
        """Test that custom blocked CIDRs are enforced."""
        resolver = fake_dns_resolver({"blocked": ["203.0.113.50"]})
        config = URLValidatorConfig(custom_blocked_cidrs=["203.0.113.0/24"])
        validator = URLValidator(config, resolve_func=resolver)

        assert validator.is_blocked("http://blocked/")

    def test_validate_raises_on_blocked(self, fake_dns_resolver):
        """Test that validate() raises SSRFBlockedError."""
        resolver = fake_dns_resolver({"localhost": ["127.0.0.1"]})
        validator = URLValidator(resolve_func=resolver)

        with pytest.raises(SSRFBlockedError):
            validator.validate("http://localhost/")

    def test_multiple_ips_one_blocked(self, fake_dns_resolver):
        """Test that if any resolved IP is blocked, the URL is blocked."""
        # Host resolves to both public and private IPs
        resolver = fake_dns_resolver({"dual-homed.com": ["93.184.216.34", "192.168.1.100"]})
        validator = URLValidator(resolve_func=resolver)

        assert validator.is_blocked("http://dual-homed.com/")

    def test_ipv6_loopback_blocked(self, fake_dns_resolver):
        """Test that IPv6 loopback is blocked."""
        resolver = fake_dns_resolver({"localhost6": ["::1"]})
        validator = URLValidator(resolve_func=resolver)

        assert validator.is_blocked("http://localhost6/")

    def test_empty_hostname_blocked(self):
        """Test that URLs without hostnames are blocked."""
        validator = URLValidator()

        assert validator.is_blocked("http:///path")
        assert validator.is_blocked("")

    def test_malformed_url_blocked(self):
        """Test that malformed URLs are blocked."""
        validator = URLValidator()

        assert validator.is_blocked("not-a-url")
        assert validator.is_blocked("://missing-scheme.com")
