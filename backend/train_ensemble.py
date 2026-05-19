import os
from app.services.forecasting.ensemble import EnsembleForecaster

data_path = r"C:\Users\psgh\Documents\ImsrProjects\forecasting\data\synthetic\daily_records.csv"

print("Training op_count model...")
op_model = EnsembleForecaster(target="op_count")
op_model.fit(data_path)
op_model.save()
print("op_count model trained and saved successfully.")

print("Training ip_count model...")
ip_model = EnsembleForecaster(target="ip_count")
ip_model.fit(data_path)
ip_model.save()
print("ip_count model trained and saved successfully.")
