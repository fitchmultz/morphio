from locust import HttpUser, between, task
import random
import string


def rand_email() -> str:
    part = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"locust_{part}@example.com"


class ApiUser(HttpUser):
    wait_time = between(0.5, 1.5)
    token: str | None = None

    def on_start(self):
        # Register a throwaway user and store token
        email = rand_email()
        payload = {
            "email": email,
            "password": "StrongP@ssw0rd!",
            "display_name": "locust_user",
        }
        with self.client.post("/auth/register", json=payload, catch_response=True) as r:
            if r.status_code == 200:
                try:
                    self.token = r.json()["data"]["access_token"]
                except Exception:
                    r.failure("missing access token")
            else:
                r.failure(f"register failed {r.status_code}")

    @task(3)
    def health(self):
        self.client.get("/health/")

    @task(2)
    def profile(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/user/profile", headers=headers)

