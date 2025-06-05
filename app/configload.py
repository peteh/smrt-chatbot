import yaml

config_file = open("app/config.yml", "r", encoding="utf-8")
configuration = yaml.safe_load(config_file)
config_file.close()

print(configuration)