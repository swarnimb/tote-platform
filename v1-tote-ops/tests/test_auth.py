"""Auth route tests — Task 5."""
import os


def test_post_login_correct_password_sets_session_and_redirects(client):
    response = client.post("/login", data={"password": os.environ["APP_PASSWORD"]}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_post_login_wrong_password_returns_200_with_error(client):
    response = client.post("/login", data={"password": "wrong"}, follow_redirects=False)
    assert response.status_code == 200
    assert "Incorrect password" in response.text


def test_get_root_without_session_redirects_to_login(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["location"]


def test_get_root_with_expired_session_redirects_to_login(expired_session_client):
    response = expired_session_client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["location"]


def test_post_logout_clears_session_and_redirects_to_login(authenticated_client):
    response = authenticated_client.post("/logout", follow_redirects=False)
    assert response.status_code == 303
    assert "/login" in response.headers["location"]
    # Confirm session is cleared — subsequent request to / should redirect
    followup = authenticated_client.get("/", follow_redirects=False)
    assert followup.status_code == 302
    assert "/login" in followup.headers["location"]
