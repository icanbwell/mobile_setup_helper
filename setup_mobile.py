import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
import sys

def is_emulator_running():
    result = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    lines = result.stdout.split("\n")
    return len(lines) >= 3

def list_avds():
    result = subprocess.run(["emulator", "-list-avds"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.split("\n")[:-1]

def start_emulator(avd_name):
    subprocess.Popen(["emulator", "-avd", avd_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def prompt_start_emulator():
    if not is_emulator_running():
        print("No emulator is currently running.")
        avds = list_avds()
        if not avds:
            print("No available AVDs (Android Virtual Devices) to start.")
            return
        print("Available AVDs:")
        for i, avd in enumerate(avds):
            print(f"{i}. {avd}")
        selected = -1
        while selected not in range(len(avds)):
            try:
                selected = int(input("Choose an AVD to start: "))
            except ValueError:
                print("Please enter a valid number.")
        start_emulator(avds[selected])

def start_long_running_process(command, dir):
    print(f"Starting: {command} in {dir}")
    process = subprocess.Popen(command, cwd=dir, shell=True)
    return process

def execute_command(command, dir=None):
    # Echo the command to the screen
    print(f"Executing: {command} in {dir}")
    if not dir:
        dir = os.getcwd()

    process = subprocess.Popen(command, cwd=dir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()

    if len(out) > 0: 
        print(f"Output: {out.decode()}")

    if process.returncode != 0:
        print(f"Error executing '{command}'")
        print(err.decode())
        exit(1)

def clone_and_install(repo, DEV_DIR):
    print(f"\nCloning {repo}")
    execute_command(f"git clone {repo}")

    repo_name = os.path.basename(repo).replace(".git", "")
    print(f"Running yarn install in {repo_name}")
    # execute_command("yarn install", os.path.join(DEV_DIR, repo_name))

def main():
    print("\nSetting up mobile emulator\n...")
    cur_dir = os.getcwd()
    DEV_DIR = input("Enter DEV_DIR (default is " + cur_dir +"): ").strip() or cur_dir
    PATCH_DIR = DEV_DIR + "/_patches"

    repos_to_clone = [
        "git@github.com:icanbwell/mfe-toolkit.git",
        "git@github.com:icanbwell/embeddables.git",
        "git@github.com:icanbwell/em-mobile-platform.git"
    ]


    # Clone and install in parallel
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(clone_and_install, repo, DEV_DIR) for i, repo in enumerate(repos_to_clone)]
        for future in futures:
            step_count = future.result()

    # mfe-toolkit prep
    print("\nMaking changes to mfe-toolkit")
    toolkit_dir = os.path.join(DEV_DIR, "mfe-toolkit")
    execute_command("git add . && git reset -q --hard", toolkit_dir)
    execute_command("rm -rf dist", toolkit_dir)
    execute_command(f"git apply -q -3 --ignore-whitespace --ignore-space-change {PATCH_DIR}/mfe-toolkit.patch", toolkit_dir)

    execute_command("yarn", toolkit_dir)
    execute_command("yarn build", toolkit_dir)
    execute_command("yarn nx run native-components:build", toolkit_dir)
    execute_command("npx yalc push dist/libs/native-components", toolkit_dir)
    execute_command("yarn nx run native-plugins:build", toolkit_dir)
    execute_command("npx yalc push dist/libs/native-plugins", toolkit_dir)

    # embeddables prep
    print("\nMaking changes to embeddables")
    embed_dir = os.path.join(DEV_DIR, "embeddables")
    execute_command("git add . && git reset -q --hard", embed_dir)
    execute_command("rm -rf dist", embed_dir)
    execute_command(f"git apply -q -3 --ignore-whitespace --ignore-space-change {PATCH_DIR}/embeddables.patch", embed_dir)
    execute_command("npx yalc add @icanbwell/native-components @icanbwell/native-plugins", embed_dir)
    execute_command("yarn", embed_dir)
    execute_command("yarn build && yarn nx run composite:build && yalc push dist/libs/composite/package", embed_dir)
    execute_command(f"cp {PATCH_DIR}/embeddables.env {embed_dir}/.env")

    # em-mobile-platform prep
    print("\nMaking changes to em-mobile-platform")
    em_dir = os.path.join(DEV_DIR, "em-mobile-platform")
    execute_command("git add . && git reset -q --hard", em_dir)
    execute_command("git fetch -q && git checkout origin/main -q", em_dir)
    execute_command("npx yalc add @icanbwell/composite @icanbwell/native-components", em_dir)
    execute_command("yarn", em_dir)
    execute_command(f"cp {PATCH_DIR}/em-mobile-platform.env {em_dir}/.env")

   # prompt_start_emulator()



    # all set
    print("\nAll set! Run the app locally and then start the emulator to see your changes.")
    print("Now run 3 commands.\n1) 'adb reverse tcp:8085 tcp:8085 && adb reverse tcp:8080 tcp:8080' to connect the android emulator to the local server.\n2) From embeddables dir (in a new terminal): yarn dev -e composite\n3) From em-mobile-platform dir (in a new terminal): yarn android")


if __name__ == "__main__":
    main()

