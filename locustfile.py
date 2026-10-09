
from locust import HttpUser, task, between

class UsuarioQMS(HttpUser):
    wait_time = between(2, 5)
    host = "http://127.0.0.1:8000"

    @task(3)
    def inicio(self):
        self.client.get("/", name="Inicio")

    @task(2)
    def login(self):
        self.client.get("/login/", name="Login")
