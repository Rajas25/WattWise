# ⚡ WattWise — ML-Based Campus Energy Waste Detection & Analytics

**Detect energy waste. Analyze consumption. Support smarter campus energy management.**

WattWise is a machine-learning-based project that analyzes campus building energy-consumption data to identify unusual usage patterns and estimate the potential financial impact of energy waste.

The project combines synthetic energy-data generation, preprocessing, regression-based prediction, anomaly detection, financial-loss estimation, and an interactive Streamlit dashboard.

## ✨ Features

- **Synthetic Energy Data Generation:** Generates sample energy-consumption data for experimentation.
- **Feature Engineering:** Prepares and processes data for machine-learning workflows.
- **Energy Consumption Prediction:** Trains three regression models to estimate expected energy consumption.
- **Anomaly Detection:** Uses an Isolation Forest baseline to identify unusual observations.
- **Waste Analysis:** Applies contextual detection logic to help identify potential energy inefficiencies.
- **Financial Impact Estimation:** Estimates potential energy-waste costs in Indian rupees (INR).
- **Interactive Dashboard:** Provides a Streamlit interface with five tabs for exploring project outputs.
- **Frontend Demonstration:** Includes a separate HTML, CSS, and JavaScript interface.
- **Testing:** Includes pytest test files for selected project functionality.

## 🛠️ Technology Stack

- Python
- Streamlit
- Machine learning and regression
- Isolation Forest
- Data preprocessing and feature engineering
- HTML, CSS, and JavaScript
- pytest
- Git and GitHub

## 📂 Project Structure

```text
WattWise/
├── app.py
├── generate_data.py
├── train_model.py
├── utils.py
├── models/
├── tests/
├── frontend/
├── docs/
├── .gitignore
└── README.md
```

The exact contents of each directory depend on the current repository. The `docs/` folder can be used for the project audit and other documentation.

## 🚀 Getting Started

### Prerequisites

- Python 3
- Git
- Visual Studio Code or another code editor

### 1. Clone the repository

```bash
git clone https://github.com/Rajas25/WattWise.git
cd WattWise
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

If `requirements.txt` is present:

```bash
python -m pip install -r requirements.txt
```

If it is not present, install the packages required by the project and create a `requirements.txt` containing the verified dependencies.

### 4. Generate sample data

```bash
python generate_data.py
```

Review the script to confirm the configured output path before running it.

### 5. Train the models

```bash
python train_model.py
```

The training script is intended to train the project's regression models and save the resulting artifacts.

### 6. Launch the dashboard

```bash
streamlit run app.py
```

Open the local URL shown in your terminal.

### 7. Run tests

```bash
python -m pytest
```

Run the commands from the project root. The actual dependencies, file paths, and execution requirements should be verified against the current source code.

## 🔄 Workflow

1. Generate synthetic energy-consumption data.
2. Preprocess the data and engineer features.
3. Train regression models to estimate expected usage.
4. Detect unusual observations using anomaly-detection techniques.
5. Assess potential energy waste.
6. Estimate the possible financial impact.
7. Visualize results in the Streamlit dashboard.

## ⚠️ Current Scope and Limitations

- The current prototype uses synthetic data rather than verified live campus electricity readings.
- Live electricity-meter and IoT sensor integration is not implemented.
- The standalone frontend demonstration is not connected to the Python dashboard backend.
- The audited implementation does not include a dedicated database/API backend or implemented authentication and role-based access control.
- Anomaly detection identifies observations for investigation; it does not independently prove that energy was wasted.
- Financial estimates depend on the assumptions, electricity rates, and data used.

## 🔮 Future Enhancements

- Integrate real-world campus energy data.
- Add live electricity-meter or IoT sensor support.
- Improve forecasting and model evaluation.
- Add building-wise energy-consumption comparisons.
- Connect the frontend to a backend API.
- Implement secure authentication and role-based access control.
- Introduce historical reports, alerts, and dashboards.
- Validate the system using real campus data.

## 🎯 Objective

WattWise explores how machine learning and data analytics can help identify potentially inefficient electricity consumption and communicate its possible financial impact, providing a foundation for future campus energy-efficiency solutions.

## 👨‍💻 Repository

GitHub: https://github.com/Rajas25/WattWise

## 📄 License

No open-source license has been specified yet. Add a `LICENSE` file if you choose to publish the project under a particular license.

---

**WattWise — Turning energy data into actionable insights.**
