import csv
import json
import matplotlib.pyplot as plt
import os
from typing import List, Tuple

try:
    from amesim import *
except ImportError:
    print('Unable to import Simcenter Amesim module.\nCheck the AME environment variable.')
else:
    print('Simcenter Amesim module is imported')

try:
  from ame_apy import *
except ImportError:
  print('Unable to import Simcenter Amesim API module.\nCheck the AME environment variable.')

##############################################################################################

class SimulationService:
   def __init__(self):
      self._initialize_amesim()

      # Temporary files are generated when running from config file
      self.temp_files = []


   def _initialize_amesim(self) -> None:
      AMEInitAPI(False)
      AMEGetAPIVersion()


   def _create_temporary_file(self, time_col, data_col, file_name):
        # Get the full path for the file in the working directory
        file_path = os.path.join(os.getcwd(), file_name)  
        self.temp_files.append(file_path)
        with open(file_path, 'w', newline='') as temp_data_file:
            csv_writer = csv.writer(temp_data_file, delimiter=' ')
            for row in zip(time_col, data_col):
                csv_writer.writerow(row)


   def _delete_temporary_files(self):
        for file_path in self.temp_files:
            os.remove(file_path)
        self.temp_files = []


   def _trim_amesim_model(self, code: str) -> str:
      """ Trim unnecessary code in the Amesim-generated model file"""
      lines = code.split('\n')

      index_create_circuit = next(
         (i for i, line in enumerate(lines) if line.startswith('AMECreateCircuit')), 
         None
      )
      index_generate_code = next(
         (i for i, line in enumerate(lines) if line.startswith('AMEGenerateCode')), 
         None
      )
      if not index_create_circuit or not index_generate_code:
         raise ValueError("Error: Unable to parse file. Please use file generated by Amesim")
      
      lines = lines[index_create_circuit : index_generate_code]
      trimmed_code = '\n'.join(lines)

      return trimmed_code


   def load_model(self, model_file: str) -> None:
      print(f"Loading model: {model_file}")
      file_extension = model_file.split('.')[-1]
      if file_extension.lower() != "py":
         raise ValueError("Error: Model file must have correct file extension: .py")
      
      with open(model_file, "r") as file:
         code = file.read()

      try:
         exec(self._trim_amesim_model(code))
      except:
         print("Error loading model")
         raise


   def set_model_parameter(self, param_name: str, param_value: str) -> None:
      """Set the parameter values for the component"""
      print(f"Setting parameter: {param_name} = {param_value}")
      try:
         AMESetParameterValue(param_name, param_value)
      except:
         print("Error setting model parameter")
         raise


   def set_model_parameter_timeseries(self, table_name: str, data_file: str) -> None:
      """Data table file must be .csv, .txt, or .data"""

      file_extension = data_file.split('.')[-1]
      if file_extension.lower() not in [".csv", ".txt", ".data"]: 
         raise ValueError(f"{file_extension}: Data file must have correct file extension: .csv, .txt, .data")
      param_name = f"filename@{table_name}"
      self.set_model_parameter(param_name, data_file)


   def set_runtime_parameters(self, start_time_s: str, stop_time_s:str, interval_s: str) -> None:

      print(f"Setting runtime parameters: start={start_time_s}, stop={stop_time_s}, interval={interval_s}")

      try:
         AMESetRunParameter("start_time_s", start_time_s)
         AMESetRunParameter("stop_time_s", stop_time_s)
         AMESetRunParameter("interval_s", interval_s)
      except:
         print("Error setting runtime parameters")
         raise


   def _parse_config_file(self, config_file: str) -> dict:
      with open(config_file, 'r') as file:
         data = json.load(file)

         required_keys = [
         "model_file", "start_time_s", "end_time_s", 
         "interval_s", "parameters", "outputs", 
         "generate_output_files"
         ]
         for key in required_keys:
            if key not in data:
               raise RuntimeError(f"Error: '{key}' is missing in the JSON config file ")
            
         return data


   def run_from_config_file(self, config_file: str) -> None:

      print(f"Running from config file: {config_file}")

      data = self._parse_config_file(config_file)

      # Load model
      self.load_model(data["model_file"])
   
      # Set constant parameters
      for param_name, value in data["parameters"].items():
         self.set_model_parameter(param_name, str(value))

      # Set timeseries parameters
      for table_name, values_dict in data["time_series_data"].items():
         time_col = values_dict.keys()
         data_col = values_dict.values()
         
         # Create a temporary file containing timeseries data
         file_name = f"{table_name}.txt"
         self._create_temporary_file(time_col, data_col, file_name)
         self.set_model_parameter_timeseries(table_name, file_name)

      # Set runtime parameters
      self.set_runtime_parameters(
         str(data["start_time_s"]),
         str(data["end_time_s"]),
         str(data["interval_s"]),
      )
      
      self.run_simulation()

      # Get output data and save to files
      for output_param in data["outputs"]:
         self.plot_variable(output_param)

      # Possibly save outputs
      if data["generate_output_files"]:
         self.save_all_output_files(data["outputs"])

      self.quit()


   def run_simulation(self) -> None:
      print("Running system simulation...")
      try:
         AMERunSimulation()
      except:
         print("Error running simulation")
         raise


   # Return an array of values for a single variable
   def get_output_values(self, variable_name: str) -> Tuple[List[float], List[float]]:
      print(f"Getting output data for variable: {variable_name}")
      try:
         pairs = AMEGetVariableValues(variable_name)
      except:
         print(f"Error retrieving output values for {variable_name}")
         raise
      time_list, data_list = zip(*pairs)
      return time_list, data_list


   # Plot an output variable over time
   def plot_variable(self, variable_name: str) -> None:
      # Get variable values
      time_values, variable_values = self.get_output_values(variable_name)

      # Plot variables
      plt.plot(time_values, variable_values, label=variable_name)
      plt.legend(loc="upper left")
      plt.xlabel("Time")
      plt.ylabel(variable_name)
      plt.grid(True)
      
      print("Close the plot to continue...")
      plt.show()


   def save_all_output_files(self, variable_names: List[str], output_path: str = None) -> None:
      print(f"Saving all output files...")

      # Save CSV data
      self.save_output_data_csv(variable_names, output_path)

      # Save all plots
      for variable_name in variable_names:
         self.save_plot_pdf(variable_name, output_path)

      return
   

   def save_output_data_csv(self, variable_names: List[str], output_path: str = None) -> None:

      if output_path is None:
         output_path = os.path.join(os.getcwd(), "output", "data.csv")
      else:
         output_path = os.path.join(output_path, "data.csv")

      # Create the output directory if it doesn't exist
      output_dir = os.path.dirname(output_path)
      if not os.path.exists(output_dir):
         os.makedirs(output_dir)
      
      print(f"Saving output data to {output_path}")

      output_data = {}
      for i, variable_name in enumerate(variable_names):
         variable_output = self.get_output_values(variable_name)
         output_data[variable_name] = variable_output[1]
         if i == 0:
            output_data["time"] = variable_output[0]
      
      # Save to CSV file with header
      with open(output_path, 'w', newline='') as csvfile:
         fieldnames = ["time"] + variable_names
         writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

         writer.writeheader()
         for i in range(len(output_data["time"])):
               row = {field: output_data[field][i] for field in fieldnames}
               writer.writerow(row)

      return
   
   
   def save_plot_pdf(self, variable_name: str, output_path: str = None) -> None:
      
      print(f"Saving plot for variable: {variable_name} at {output_path}")

      # Get variable values
      time_values, variable_values = self.get_output_values(variable_name)

      # Plot variables
      plt.plot(time_values, variable_values, label=variable_name)
      plt.legend(loc="upper left")
      plt.xlabel("Time")
      plt.ylabel(variable_name)
      plt.grid(True)

      if output_path is None:
         output_path = os.path.join(os.getcwd(), "output", f"{variable_name}.pdf")
      else:
         output_path = os.path.join(output_path, f"{variable_name}.pdf")

      # Create the output directory if it doesn't exist
      output_dir = os.path.dirname(output_path)
      if not os.path.exists(output_dir):
         os.makedirs(output_dir)
      
      plt.savefig(output_path)
      return
   

   def quit(self):
      print(f"Quitting Simulation Service...")
      self._delete_temporary_files()
      AMECloseCircuit(True)
      AMECloseAPI(False)