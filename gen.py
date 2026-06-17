
import os
os.makedirs("src/planning",exist_ok=True)
os.makedirs("src/navigation",exist_ok=True)
os.makedirs("src/autonomy",exist_ok=True)
os.makedirs("src/telemetry",exist_ok=True)
with open("src/planning/test_write.txt","w") as f: f.write("ok")
print("Write test:",os.path.exists("src/planning/test_write.txt"))
