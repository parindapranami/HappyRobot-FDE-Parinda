# HappyRobot: Take Home Challenge

## Overview: Implemented a real-world carrier sales use case using the HappyRobot platform and developed a custom REST API to support this use case.

## Features: 
1. load matching using reference number, 
2. verification of carrier's details using MC Number, 
3. AI based extraction and classifcation from call transcript, 
4. fast loop-ups using indexing, 
5. HTTPS and Authorisation using API_KEY and Cloud service[Render]
6. Dockerisation and packaging
7. Deployed, ready to use API endpoints. 

## 📂 Folder Structure

``` 
HAPPYROBOT/
├── __pycache__/
├── venv/
├── .dockerignore
├── .env.example
├── .gitignore
├── app.py
├── Dockerfile
├── loads.csv
├── README.md
├── render.yaml
└── requirements.txt 
```

## 🛠 Tech Stack

- **Language:** Python 
- **Framework:** Flask 
- **Web Server:** Gunicorn
- **Data Handling:** Pandas
- **API Requests:** Requests library
- **Environment Variables Management:** Python-dotenv
- **Containerization:** Docker
- **Deployment Platform:** Render


## 🔑 Environment Variables
This project requires the following environment variables to be set:

| Variable | Description |
|:---------|:------------|
| `FMCSA_API_KEY` | Your FMCSA API key for verifying carrier information |
| `API_KEY` | Internal API key for authenticating requests to the backend |


## Docker
- The flask app has been dockerized and deployed at Render at: https://happyrobot-parinda.onrender.com


## Deployment Details
- This Flask API is **Dockerized** and **deployed on [Render](https://render.com/)**.
- The service is set up as a **Docker Web Service**, built directly from the `Dockerfile` in the GitHub repository.
- Every push to the **main branch** automatically triggers a new build and deploy on Render.
-  As this is hosted on a **free Render instance**, there may be a short delay (cold start latency) on the first request after periods of inactivity.
- Environment variables such as `FMCSA_API_KEY` and `API_KEY` are securely managed in Render's dashboard.
- The app is publicly accessible at:  https://happyrobot-parinda.onrender.com and https://github.com/parindapranami/HappyRobot-FDE-Parinda

## API Endpoints
### A) find_available_loads: 
1. Request Type: `POST` request.

2. Authentication: Requires an `x-api-key` header matching the internal API key (`API_KEY` from environment).

3. Input Options
    - **Option 1:** Provide a `reference_number` (integer) to directly fetch a load.
    - **Option 2:** Provide a combination of `origin`, `destination`, and `equipment_type` to search for matching loads.

4. Behavior
    - If `reference_number` is valid and found, it returns the specific load details.
    - If `origin`, `destination`, and `equipment_type` are provided, it searches the database (`loads.csv`) for matching loads.
    - If no match is found, returns a **404 Not Found** error with an appropriate message.
    - If neither option is properly provided, returns a **400 Bad Request** error.

5. Response Example

- Successful lookup:
    ```json
    {
    "reference_number": 12345,
    "origin": "Los Angeles, CA",
    "destination": "Phoenix, AZ",
    "equipment_type": "Flatbed",
    "rate": 950,
    "commodity": "Building Materials"
    }
    ```

- Error Response:
    ```json
    {
    "error": "Load not found by reference number"
    }
    ```

6. Design Considerations for `/find_available_loads`

- **Flexible Matching:**  
    1. Instead of exact matches, the API uses **case-insensitive substring matching** for `origin`, `destination`, and `equipment_type`.  
    2. This allows partial matches like `"LA"` matching `"Los Angeles"`, improving usability and accommodating minor differences in input.

- **Reference Number Priority:** If a valid `reference_number` is provided, it is prioritized for direct lookup using the indexed DataFrame for faster access.

- **Efficient Lookup:** The `loads.csv` file is preloaded into a **pandas DataFrame**, with `reference_number` set as the index for **O(1)** direct load retrieval based on reference numbers.

- **Load Data Source (`loads.csv`):** The load information is read from a CSV file with the following structure:

  | reference_number | origin        | destination   | equipment_type     | rate | commodity           |
  |------------------|---------------|---------------|--------------------|------|---------------------|
  | 09460             | Denver, CO    | Detroit, MI   | Dry Van             | 868  | Automotive Parts     |
  | 04684             | Dallas, TX    | Chicago, IL   | Dry Van or Flatbed  | 570  | Agricultural Products |
  | 09690             | Detroit, MI   | Nashville, TN | Dry Van             | 1495 | Industrial Equipment  |
  | 12345             | Los Angeles, CA | Phoenix, AZ | Flatbed             | 950  | Building Materials    |
  | 67890             | Atlanta, GA   | Orlando, FL   | Dry Van             | 725  | Consumer Goods        |
  | 24680             | Seattle, WA   | Portland, OR  | Refrigerated        | 1200 | Frozen Foods          |
  | 13579             | Miami, FL     | Houston, TX   | Dry Van             | 1100 | Pharmaceuticals       |
  | 98765             | New York, NY  | Boston, MA    | Dry Van or Reefer   | 850  | Electronics           |

- **Error Handling:**  
   1. If no matching loads are found, the API returns a clear **404 Not Found** error.
   2. If insufficient or invalid parameters are provided, it returns a **400 Bad Request** error with an appropriate message.

- **Input Validation:**  
   1. Attempts to convert `reference_number` to an integer and validates its existence in the dataset.
   2. Ensures `origin`, `destination`, and `equipment_type` fields are present when performing lane-based search.

- **Security:** API access is restricted via a custom decorator checking for a valid `x-api-key` in the request headers.

### B) verify_carrier:
1. Request Type: `GET` request.

2. Authentication: Requires an `x-api-key` header matching the internal API key (`API_KEY` from environment).

3. Input Parameters:
  - **Query Parameter:** `mc_number` (string or number)  
  - Accepts an MC number with or without the `'MC'` prefix.
  - Non-digit characters are stripped internally.

4. Behavior:
- The API first uses the **MC number/Docket number** to fetch the corresponding **DOT number** and **legal name** by querying the FMCSA API (`/docket-number/{mc_number}` endpoint).
- If no carrier is found for the given MC number, a **404 Not Found** error is returned.
- If a DOT number is successfully retrieved, the API queries the FMCSA API (`/{dot_number}/operation-classification`) to check the **operation classification**.
- The carrier is considered **verified** only if its classifications include **"Authorized For Hire"**.
- Otherwise, verification fails with an appropriate reason.

5. Response Example:

- Successful verification:
    ```json
    {
    "verified": true,
    "legal_name": "Sample Carrier",
    "dot_number": "1234567",
    "reason": null
    }
    ```

- Failure when not authorized:
    ```json
    {
    "verified": false,
    "legal_name": "Sample Carrier",
    "dot_number": "1234567",
    "reason": "Carrier is not authorized"
    }
    ```

- Error when MC number not found:
    ```json
    {
    "verified": false,
    "legal_name": null,
    "dot_number": null,
    "reason": "No carrier found for given MC number"
    }
    ```
6. Design Considerations for `/verify_carrier`

    - **Handling Different Number Formats:**  MC numbers with prefixes like `'MC'` or non-digit characters are normalized automatically to handle both traditional and newer formats.

    - **Two-Step Verification Flow:**  
        1. First, use the MC number to find the corresponding DOT number (since FMCSA's newer data sometimes only recognizes DOT numbers).
        2. Then, validate the DOT number by checking if the carrier's operation classification includes **"Authorized For Hire"**.

    - **Security:** API access is restricted via a custom decorator that checks for a valid `x-api-key` in the request headers.

    - **Error Handling:** Provides clear distinctions between:
        1. Missing MC numbers
        2. Invalid MC numbers (no carrier found)
        3. Carriers found but not authorized for hire

## Credits
- Developed by Parinda Pranami: https://www.linkedin.com/in/parindapranami/
- Used the platform provided by HappyRobot: https://docs.happyrobot.ai/general/introduction

## Future Improvements
- Configure SIP and trunk setting for the web call 
- Actually make the transfer call 
