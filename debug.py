import subprocess
import webbrowser

subprocess.run(["jupyter", "lab"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)