import os
LOG_DIR = "./flight_logs"

filename = input("Enter log filename: ")

try:
    f = open(os.path.join(LOG_DIR, filename), "r")
except FileNotFoundError:
    print(f"File {filename} not found in {LOG_DIR}.")
    exit(1)

types = input("Enter log types to keep (comma separated) (INFO, DEBUG, WARNING, ERROR, CRITICAL, all): ").split(",")
types = [t.strip().upper() for t in types]
if len(types) == 0:
    print("No types specified. Exiting.")
    exit(1)
if len(types) == 1 and types[0] == "":
    print("No types specified. Exiting.")
    exit(1)
if len(types) == 1 and types[0] == "ALL":
    print("Keeping all log types.")
    types = ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]

modules = input("Enter log modules to keep (comma separated) (States, Actions, Flight, Controller, Mission, all): ").split(",")
modules = [m.strip().title() for m in modules]
if len(modules) == 0:
    print("No modules specified. Exiting.")
    exit(1)
if len(modules) == 1 and modules[0] == "":
    print("No modules specified. Exiting.")
    exit(1)
if len(modules) == 1 and modules[0] == "All":
    print("Keeping all log modules.")
    modules = ["States", "Actions", "Flight", "Controller", "Mission"]

# Read the file and filter the lines
filtered_lines = []
for line in f:
    # Check if the line contains a log type
    if any(f"{t}" in line for t in types):
        # Check if the line contains a log module
        if any(f"[{m}]" in line for m in modules):
            filtered_lines.append(line)
        else:
            # Check if the line contains a log module with a different case
            if any(f"[{m.lower()}]" in line.lower() for m in modules):
                filtered_lines.append(line)
    else:
        # Check if the line contains a log type with a different case
        if any(f"{t.lower()}" in line.lower() for t in types):
            filtered_lines.append(line)

f.close()

# Write the filtered lines to a new file
outfile = input("Enter output filename (leave blank to overwrite original): ")
if outfile == "":
    outfile = filename
outfile = os.path.join(LOG_DIR, outfile)
with open(outfile, "w") as f:
    f.writelines(filtered_lines)
print(f"Filtered log written to {outfile}.")
f.close()



