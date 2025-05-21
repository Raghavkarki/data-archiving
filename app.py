from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
import base64
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure random key in production

COUCHDB_URL = "https://qa.sambhavpossible.org/medic"
USERNAME = "medic"
PASSWORD = "password"

def encode_credentials(username, password):
    credentials = f"{username}:{password}"
    return base64.b64encode(credentials.encode()).decode()

def create_headers():
    return {
        "Accept": "application/json",
        "Authorization": f"Basic {encode_credentials(USERNAME, PASSWORD)}"
    }

FORM_NAME_MAPPING = {
    "u2_registry": "U2 Registry",
    "anc_monitoring": "ANC Monitoring-old",
    "anc_monitoring_form": "ANC Monitoring-new", 
    "pregnancy_screening_form": "Pregnancy Screening Form",
    "epds_module_5": "EPDS Module 5",
    "epds_module_1": "EPDS Module 1",
    "epds_module_2": "EPDS Module 2",
    "post_delivery_form": "Post Delivery Form",
    "epds_screening": "EPDS Screening",
    # Add more mappings as needed
}

def fetch_reports_by_contact_id(contact_id):
    try:
        url = f"{COUCHDB_URL}/_all_docs?include_docs=true"
        response = requests.get(url, headers=create_headers(), verify=False)
        if response.status_code != 200:
            return None
        data = response.json()
        filtered_docs = [
            row for row in data['rows']
            if row.get('doc', {}).get('fields', {}).get('inputs', {}).get('contact', {}).get('_id') == contact_id
        ]
        return filtered_docs if filtered_docs else None
    except Exception as e:
        print(f"Error fetching reports: {e}")
        return None

VALID_USERNAME = "admin"
VALID_PASSWORD = "admin123"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    result_messages = []
    records = []
    report_ids = []
    selected_form_names = []

    if request.method == "POST":
        input_ids = request.form.get("report_ids", "")
        selected_form_names = request.form.getlist("form_name")
        report_ids = [id.strip() for id in input_ids.split(",") if id.strip()]

        if not report_ids:
            result_messages.append({"message": "Please enter at least one Report ID.", "type": "error"})
        else:
            for contact_id in report_ids:
                filtered = fetch_reports_by_contact_id(contact_id)
                if filtered:
                    if selected_form_names:
                        filtered = [doc for doc in filtered if doc.get('doc', {}).get('form') in selected_form_names]
                    if filtered:
                        records.extend(filtered)
                        result_messages.append({
                            "message": f"Successfully fetched reports for contact._id = {contact_id}.",
                            "type": "success"
                        })
                    else:
                        readable_names = ", ".join(FORM_NAME_MAPPING.get(f, f) for f in selected_form_names)
                        result_messages.append({
                            "message": f"No records found for contact._id = {contact_id} with form(s): {readable_names}.",
                            "type": "error"
                        })
                else:
                    result_messages.append({
                        "message": f"No records found with contact._id = {contact_id}.",
                        "type": "error"
                    })

    return render_template(
        "index.html",
        result_messages=result_messages,
        records=records,
        report_ids=report_ids,
        form_name_mapping=FORM_NAME_MAPPING,
        selected_form_names=selected_form_names
    )

@app.route("/delete-report", methods=["POST"])
def delete_report():
    if not session.get("logged_in"):
        return jsonify(success=False, message="Unauthorized")

    data = request.get_json()
    doc_id = data.get("docId")
    rev = data.get("rev")

    try:
        delete_url = f"{COUCHDB_URL}/{doc_id}?rev={rev}"
        response = requests.delete(delete_url, headers=create_headers(), verify=False)
        if response.status_code == 200:
            return jsonify(success=True, message=f"Report {doc_id} deleted successfully.")
        else:
            return jsonify(success=False, message=f"Failed to delete report {doc_id}.")
    except Exception as e:
        return jsonify(success=False, message=f"Error deleting report: {e}")

@app.route("/delete-all-reports", methods=["POST"])
def delete_all_reports():
    if not session.get("logged_in"):
        return jsonify(success=False, message="Unauthorized")

    data = request.get_json()
    report_ids = data.get("reportIds", [])
    results = []

    try:
        for doc_id in report_ids:
            fetch_url = f"{COUCHDB_URL}/{doc_id}"
            fetch_response = requests.get(fetch_url, headers=create_headers(), verify=False)
            if fetch_response.status_code == 200:
                rev = fetch_response.json().get("_rev")
                delete_url = f"{COUCHDB_URL}/{doc_id}?rev={rev}"
                delete_response = requests.delete(delete_url, headers=create_headers(), verify=False)
                if delete_response.status_code == 200:
                    results.append({"docId": doc_id, "success": True, "message": f"Report {doc_id} deleted successfully."})
                else:
                    results.append({"docId": doc_id, "success": False, "message": f"Failed to delete report {doc_id}."})
            else:
                results.append({"docId": doc_id, "success": False, "message": f"Failed to fetch report {doc_id}."})
        return jsonify(success=True, results=results)
    except Exception as e:
        return jsonify(success=False, message=f"Error deleting reports: {e}")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
