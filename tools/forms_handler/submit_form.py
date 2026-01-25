import requests



FORM_ID = "1FAIpQLSd7t0xnMvNcwR-0f5pQZFgUaBMolae6xMhuvHznBQM5_CcC4A"
FORM_RESPONSE_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/formResponse"


def submit_problem_metadata(
    team_name: str,
    member_id: str,
    requester_role: str,
    team_id: str,
    email_id: str,
    xml_file_link: str | None = None,
    python_file_link: str | None = None,
    bug_file_link: str | None = None,
) -> bool:
    """
    Submit Google Form response via HTTP POST.
    NOTE:
    - File uploads are NOT supported via POST
    - Upload files separately and pass links instead
    """
    print(f"[DEBUG] submit_problem_metadata called with: team_name={team_name}, member_id={member_id}, requester_role={requester_role}, team_id={team_id}, email_id={email_id}")
    print(f"[DEBUG] Optional file links: xml_file_link={xml_file_link}, python_file_link={python_file_link}, bug_file_link={bug_file_link}")

    payload = {
    "entry.975974606": team_name,
    "entry.1125040411": member_id,
    "entry.860492623": requester_role,
    "entry.68192247": team_id,
    "entry.1430184370": email_id,
    }

    if xml_file_link:
        payload["entry.283229220"] = xml_file_link

    if python_file_link:
        payload["entry.167624718"] = python_file_link

    if bug_file_link:
        payload["entry.2103092288"] = bug_file_link

    print(f"[DEBUG] Payload constructed: {payload}")
    print(f"[DEBUG] Sending POST request to: {FORM_RESPONSE_URL}")

    res = requests.post(
        FORM_RESPONSE_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )

    print(f"[DEBUG] Response received - Status Code: {res.status_code}")
    print(f"[DEBUG] Response URL: {res.url}")
    if res.status_code != 200:
        print(f"[DEBUG] Error response text: {res.text[:200]}")  # First 200 chars of error response
    
    result = res.status_code == 200
    print(f"[DEBUG] Function returning: {result}")
    return result
