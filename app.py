from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
from functools import wraps
import pandas as pd


app = Flask(__name__)
load_dotenv()

# indexing for faster lookups and efficient querying
loads_df = pd.read_csv('loads.csv', index_col='reference_number')


API_KEY = os.getenv("API_KEY", "PERSONAL_API_KEY")
def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if request.headers.get('x-api-key') == API_KEY:
            return view_function(*args, **kwargs)
        else:
            return jsonify({"error": "Unauthorized"}), 401
    return decorated_function


FMCSA_API_KEY = os.getenv("FMCSA_API_KEY", "YOUR_API_KEY")
if not FMCSA_API_KEY or FMCSA_API_KEY == "YOUR_API_KEY":
    raise ValueError("FMCSA_API_KEY not set! Please check environment variables.")



# Base URL for FMCSA API
FMCSA_API_BASE = "https://mobile.fmcsa.dot.gov/qc/services/carriers"


# Step 1: Get DOT number from MC number
def get_dot_number_from_mc(MC_number):
    try:
        url = f"{FMCSA_API_BASE}/docket-number/{MC_number}?webKey={FMCSA_API_KEY}"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        
        if not data.get("content"):
            return None, None
        carrier = data["content"][0]["carrier"]
        return carrier.get("dotNumber"), carrier.get("legalName")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")  # or logging
        return None, None


# Step 2: Check if operation classification includes "Authorized For Hire"
def is_authorized_for_hire(dot_number): 
    try:
        url = f"{FMCSA_API_BASE}/{dot_number}/operation-classification?webKey={FMCSA_API_KEY}"
        resp = requests.get(url)
        resp.raise_for_status()
        classes = [entry["operationClassDesc"] for entry in resp.json().get("content", [])]
        return "Authorized For Hire" in classes
    except requests.exceptions.RequestException as e:
        print(f"Request error in is_authorized_for_hire: {e}")  # replace with logging later if i need
        return False



# Step 3: Verify the carrier using the MC number
@app.route('/verify_carrier', methods=['GET'])
@require_api_key
def verify_carrier():
    try:
        mc_number = request.args.get('mc_number')
        if not mc_number:
            return jsonify({"error": "Missing mc_number parameter"}), 400
        
        # Remove 'MC' prefix if exists
        mc_number = ''.join(filter(str.isdigit, mc_number))
       
        dot_number, legal_name = get_dot_number_from_mc(mc_number)
        if not dot_number:
            return jsonify({
                "verified": False,
                "legal_name": None,
                "dot_number": None,
                "reason": "No carrier found for given MC number"
            }), 404  
        authorized = is_authorized_for_hire(dot_number)
        verified = authorized
        return jsonify({
            "verified": verified,
            "legal_name": legal_name,
            "dot_number": dot_number,
            "reason": None if verified else "Carrier is not authorized"
        })
    except Exception as e:
        return jsonify({
            "verified": False,
            "reason": f"Internal server error: {str(e)}"
        }), 500



# Step 4: Find available loads based on reference number or lane_trailer_type
@app.route('/find_available_loads', methods=['POST'])
@require_api_key
def find_available_loads():
    data = request.get_json()
    reference_number = data.get('reference_number')
    origin = data.get('origin')
    destination = data.get('destination')
    equipment_type = data.get('equipment_type')

    if reference_number not in [None, ""]:
        try:
            reference_number = int(reference_number)
        except ValueError:
            return jsonify({"error": "reference_number must be an integer"}), 400
        
        if reference_number not in loads_df.index:
            return jsonify({"error": "Load not found by reference number"}), 404

        load = loads_df.loc[[reference_number]]  
        return jsonify(load.to_dict(orient='records')[0])
    
    elif origin and destination and equipment_type:
        filtered = loads_df[
        (loads_df['origin'].str.contains(origin, case=False, na=False)) &
        (loads_df['destination'].str.contains(destination, case=False, na=False)) &
        (loads_df['equipment_type'].str.contains(equipment_type, case=False, na=False))
        ]
        if filtered.empty:
            return jsonify({"error": "No matching loads found by lane and equipment"}), 404
        return jsonify(filtered.to_dict(orient='records'))
        
    else:
        return jsonify({"error": "Insufficient information. Provide either reference_number or (origin, destination, equipment_type)."}), 400

#HTTPS will be handled by the cloud provider
if __name__ == '__main__':
    app.run()