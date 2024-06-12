import argparse

from simulation_service import SimulationService


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", type=str, help="path to the configuration data (.json)", required=True)

    return parser.parse_args()


def _main():
   args = parse_args()

   config_file = args.config

   simulation_service = SimulationService()
   
   simulation_service.run_from_config_file(config_file)
   

if __name__ == '__main__':
    _main()

