use ahash::AHashMap;
use pyo3::prelude::*;
use regex::Regex;
use std::net::Ipv4Addr;
use std::str::FromStr;
use std::sync::OnceLock;
use xxhash_rust::xxh3::xxh3_64;

use crate::types::AnonymizationResult;

static PATTERNS: OnceLock<Vec<(Regex, &'static str)>> = OnceLock::new();

fn get_patterns() -> &'static Vec<(Regex, &'static str)> {
    PATTERNS.get_or_init(|| {
        vec![
            (
                Regex::new(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}").unwrap(),
                "EMAIL",
            ),
            (
                Regex::new(r"(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}")
                    .unwrap(),
                "PHONE",
            ),
            (
                Regex::new(r"\b(?:\d{4}[-\s]?){3}\d{4}\b").unwrap(),
                "CREDIT_CARD",
            ),
            (Regex::new(r"\b\d{3}-\d{2}-\d{4}\b").unwrap(), "SSN"),
            // IP pattern handled separately with validation
        ]
    })
}

static IP_PATTERN: OnceLock<Regex> = OnceLock::new();

fn get_ip_pattern() -> &'static Regex {
    IP_PATTERN.get_or_init(|| Regex::new(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b").unwrap())
}

fn get_or_create_placeholder(
    original: &str,
    prefix: &'static str,
    mapping: &mut AHashMap<String, String>,
    reverse_mapping: &mut AHashMap<String, String>,
    counters: &mut AHashMap<&'static str, usize>,
) -> String {
    if let Some(placeholder) = mapping.get(original) {
        return placeholder.clone();
    }

    let count = counters.entry(prefix).or_insert(0);
    *count += 1;
    let placeholder = format!("[{prefix}_{count}]");

    mapping.insert(original.to_string(), placeholder.clone());
    reverse_mapping.insert(placeholder.clone(), original.to_string());
    placeholder
}

#[pyfunction]
pub fn anonymize(content: &str) -> PyResult<AnonymizationResult> {
    let mut mapping: AHashMap<String, String> = AHashMap::new();
    let mut reverse_mapping: AHashMap<String, String> = AHashMap::new();
    let mut counters: AHashMap<&'static str, usize> = AHashMap::new();
    let mut result = content.to_string();

    // Apply non-IP patterns (preserves Python order)
    for (regex, prefix) in get_patterns().iter() {
        result = regex
            .replace_all(&result, |caps: &regex::Captures| {
                let matched = caps.get(0).unwrap().as_str();
                get_or_create_placeholder(
                    matched,
                    prefix,
                    &mut mapping,
                    &mut reverse_mapping,
                    &mut counters,
                )
            })
            .to_string();
    }

    // Apply IP pattern with validation (matches Python ipaddress.IPv4Address behavior)
    let ip_regex = get_ip_pattern();
    result = ip_regex
        .replace_all(&result, |caps: &regex::Captures| {
            let ip = caps.get(1).unwrap().as_str();
            // Validate using std::net::Ipv4Addr (same validation as Python ipaddress module)
            if Ipv4Addr::from_str(ip).is_ok() {
                get_or_create_placeholder(
                    ip,
                    "IP_ADDRESS",
                    &mut mapping,
                    &mut reverse_mapping,
                    &mut counters,
                )
            } else {
                ip.to_string() // Invalid IP - leave unchanged
            }
        })
        .to_string();

    let content_hash = format!("{:016x}", xxh3_64(result.as_bytes()));

    Ok(AnonymizationResult::new(
        result,
        mapping.into_iter().collect(),
        reverse_mapping.into_iter().collect(),
        content_hash,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_anonymize_email() {
        let result = anonymize("Contact me at test@example.com").unwrap();
        assert!(result.text.contains("[EMAIL_1]"));
        assert!(!result.text.contains("test@example.com"));
        assert_eq!(
            result.mapping.get("test@example.com"),
            Some(&"[EMAIL_1]".to_string())
        );
    }

    #[test]
    fn test_anonymize_phone() {
        let result = anonymize("Call me at 555-123-4567").unwrap();
        assert!(result.text.contains("[PHONE_1]"));
        assert!(!result.text.contains("555-123-4567"));
    }

    #[test]
    fn test_anonymize_ssn() {
        let result = anonymize("SSN: 123-45-6789").unwrap();
        assert!(result.text.contains("[SSN_1]"));
        assert!(!result.text.contains("123-45-6789"));
    }

    #[test]
    fn test_anonymize_credit_card() {
        let result = anonymize("Card: 1234-5678-9012-3456").unwrap();
        assert!(result.text.contains("[CREDIT_CARD_1]"));
        assert!(!result.text.contains("1234-5678-9012-3456"));
    }

    #[test]
    fn test_anonymize_valid_ip() {
        let result = anonymize("Server at 192.168.1.1").unwrap();
        assert!(result.text.contains("[IP_ADDRESS_1]"));
        assert!(!result.text.contains("192.168.1.1"));
    }

    #[test]
    fn test_anonymize_invalid_ip() {
        // 999.999.999.999 is invalid - should not be anonymized
        let result = anonymize("Invalid: 999.999.999.999").unwrap();
        assert!(result.text.contains("999.999.999.999"));
        assert!(!result.text.contains("[IP_ADDRESS_"));
    }

    #[test]
    fn test_duplicate_values_same_placeholder() {
        let result = anonymize("Email: test@example.com and again test@example.com").unwrap();
        // Both occurrences should use the same placeholder
        let count = result.text.matches("[EMAIL_1]").count();
        assert_eq!(count, 2);
        assert!(!result.text.contains("[EMAIL_2]"));
    }

    #[test]
    fn test_content_hash_deterministic() {
        let result1 = anonymize("test@example.com").unwrap();
        let result2 = anonymize("test@example.com").unwrap();
        assert_eq!(result1.content_hash, result2.content_hash);
    }
}
