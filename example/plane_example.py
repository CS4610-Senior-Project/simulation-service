from simulation_service import SimulationService

ss = SimulationService()

ss.load_model("models/plane.py")

ss.set_model_parameter("veGxbinit@aero_fd_6dof_body", "5")
ss.set_model_parameter("veGzbinit@aero_fd_6dof_body", "3")

ss.set_model_parameter_timeseries("dynamic_time_table", "data/throttle.csv")

ss.set_runtime_parameters(
   start_time_s = "1",
   end_time_s = "10",
   interval_s = "0.1",
)

ss.run_simulation()

thrust_vals = ss.get_output_values("thrust@aero_fd_6dof_thrust")

ss.plot_variable("thrust@aero_fd_6dof_thrust")

ss.quit()
