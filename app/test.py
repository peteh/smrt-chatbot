import re
text = """- It interviews a former police officer who reveals some problems within the police culture and organization[^4^].
  - It examines a case where a police officer was convicted of assault thanks to a colleague who testified against him[^5^]."""
text = re.sub("\[\^[0-9]+\^\]", "", text)

print(text)