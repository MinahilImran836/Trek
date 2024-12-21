import os
import json
import hashlib
from datetime import datetime
import difflib
from colorama import Fore, init

init(autoreset=True)

undo_stack = []
redo_stack = []


def is_ignored(file_path):
    ignore_path = os.path.join(os.getcwd(), ".Trek", ".gitignore")

    if not os.path.exists(ignore_path):
        return False

    with open(ignore_path, "r") as ignore_file:
        ignore_patterns = ignore_file.readlines()

    ignore_patterns = [pattern.strip() for pattern in ignore_patterns]

    for pattern in ignore_patterns:
        if pattern and file_path.endswith(pattern):
            return True
    return False


def get_current_commit():
    repo_path = os.path.join(os.getcwd(), ".Trek")
    head_path = os.path.join(repo_path, "HEAD")
    with open(head_path, "r") as head_file:
        head = head_file.read().strip()
    if head.startswith("ref: "):
        branch_path = os.path.join(repo_path, head[5:])
        with open(branch_path, "r") as branch_file:
            return branch_file.read().strip()
    return head


def init():
    repo_path = os.path.join(os.getcwd(), ".Trek")

    if os.path.exists(repo_path):
        print(f"{Fore.RED}Repository already exists!")
        return

    os.makedirs(os.path.join(repo_path, "objects"))
    os.makedirs(os.path.join(repo_path, "refs", "heads"))
    os.makedirs(os.path.join(repo_path, "refs", "tags"))

    master_branch_path = os.path.join(repo_path, "refs", "heads", "master")
    with open(master_branch_path, "w") as master_file:
        master_file.write("")

    with open(os.path.join(repo_path, "HEAD"), "w") as head_file:
        head_file.write("ref: refs/heads/master\n")

    with open(os.path.join(repo_path, ".gitignore"), "w") as ignore_file:
        ignore_file.write("")

    print(
        f"{Fore.LIGHTGREEN_EX}Initialized {Fore.RED} empty {Fore.LIGHTGREEN_EX} repository with {Fore.YELLOW} master {Fore.LIGHTGREEN_EX} branch."
    )


def add(files):
    repo_path = os.path.join(os.getcwd(), ".Trek")
    index_path = os.path.join(repo_path, "index")

    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a Trek repository!")
        return

    index = {}
    if os.path.exists(index_path):
        with open(index_path, "r") as index_file:
            index = json.load(index_file)

    for file in files:
        if is_ignored(file):
            print(
                f"{Fore.YELLOW}File {Fore.LIGHTMAGENTA_EX}{file}{Fore.YELLOW} is ignored due to .gitignore"
            )
            continue

        if not os.path.exists(file):
            print(f"{Fore.RED}File {file} not found")
            continue

        with open(file, "rb") as f:
            content = f.read()
            file_hash = hashlib.sha1(content).hexdigest()
            object_path = os.path.join(repo_path, "objects", file_hash)
            if not os.path.exists(object_path):
                with open(object_path, "wb") as object_file:
                    object_file.write(content)

            index[file] = file_hash

    with open(index_path, "w") as index_file:
        json.dump(index, index_file, indent=2)

    print(
        f"{Fore.LIGHTGREEN_EX}Added {Fore.CYAN} {len(files)} {Fore.LIGHTGREEN_EX} files to the staging area."
    )


def commit(message):
    repo_path = os.path.join(os.getcwd(), ".Trek")
    index_path = os.path.join(repo_path, "index")

    if not os.path.exists(repo_path):
        print(f"{Fore.RED} Not a Trek repository")
        return

    if not os.path.exists(index_path):
        print(f"{Fore.RED}Nothing to commit")
        return

    # Load the staged index
    with open(index_path, "r") as index_file:
        index = json.load(index_file)

    if not index:  # Check if the index is empty
        print(f"{Fore.RED}Nothing to commit")
        return

    head_path = os.path.join(repo_path, "HEAD")
    with open(head_path, "r") as head_file:
        head = head_file.read().strip()

    parent_commit = None
    if head.startswith("ref: "):  # If HEAD points to a branch
        branch_path = os.path.join(repo_path, head[5:])
        if os.path.exists(branch_path):
            with open(branch_path, "r") as branch_file:
                parent_commit = branch_file.read().strip()

    # Prepare tree object for this commit
    tree_content = "\n".join(
        [f"{file_hash} {file}" for file, file_hash in index.items()]
    )
    tree_hash = hashlib.sha1(tree_content.encode("utf-8")).hexdigest()
    tree_path = os.path.join(repo_path, "objects", tree_hash)

    if not os.path.exists(tree_path):  # Create tree object if it doesn't exist
        os.makedirs(os.path.dirname(tree_path), exist_ok=True)
        with open(tree_path, "w") as tree_file:
            tree_file.write(tree_content)

    # Create commit object
    commit_content = f"tree {tree_hash}\n"
    if parent_commit:
        commit_content += f"parent {parent_commit}\n"
    commit_content += f"author User <user@example.com>\n"
    commit_content += (
        f"date {datetime.now().strftime('%a %b %d %H:%M:%S %Y')}\n\n{message}\n"
    )
    commit_hash = hashlib.sha1(commit_content.encode("utf-8")).hexdigest()

    commit_path = os.path.join(repo_path, "objects", commit_hash)
    if not os.path.exists(commit_path):  # Create commit object if it doesn't exist
        os.makedirs(os.path.dirname(commit_path), exist_ok=True)
        with open(commit_path, "w") as commit_file:
            commit_file.write(commit_content)
    undo_stack.append(get_current_commit())
    # Update branch reference
    if head.startswith("ref: "):
        branch_path = os.path.join(repo_path, head[5:])
        with open(branch_path, "w") as branch_file:
            branch_file.write(commit_hash)
    else:
        with open(head_path, "w") as head_file:
            head_file.write(commit_hash)

    # Clear the index (reset the staging area)
    with open(index_path, "w") as index_file:
        json.dump({}, index_file)

    print(f"{Fore.YELLOW}[{commit_hash[:7]}] {Fore.CYAN}{message}")


def undo():

    if not undo_stack:
        print(f"{Fore.RED}Nothing to undo.")
        return

    commit_to_undo = undo_stack.pop()
    redo_stack.append(get_current_commit())
    reset(commit_to_undo, hard=True)
    print(
        f"{Fore.LIGHTGREEN_EX}Undo successful. Reverted to {Fore.YELLOW}{commit_to_undo}"
    )


def redo():
    global undo_stack, redo_stack

    if not redo_stack:
        print(f"{Fore.RED}Nothing to redo.")
        return

    commit_to_redo = redo_stack.pop()
    undo_stack.append(get_current_commit())
    reset(commit_to_redo, hard=True)
    print(
        f"{Fore.LIGHTGREEN_EX}Redo successful. Reverted to  {Fore.YELLOW}{commit_to_redo}"
    )


def branch(name=None):
    repo_path = os.path.join(os.getcwd(), ".Trek")

    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a Trek repository!")
        return

    branches_path = os.path.join(repo_path, "refs", "heads")

    if name is None:
        branches = os.listdir(branches_path)
        if branches:
            print(f"{Fore.CYAN}Branches:")
            for branch in branches:
                print(f"  {Fore.YELLOW}{branch}")
        else:
            print(f"{Fore.RED}No branches found.")
        return

    head_path = os.path.join(repo_path, "HEAD")
    with open(head_path, "r") as head_file:
        head = head_file.read().strip()

    current_commit = ""
    if head.startswith("ref: "):
        current_branch_path = os.path.join(repo_path, head[5:])
        with open(current_branch_path, "r") as current_branch_file:
            current_commit = current_branch_file.read().strip()
    else:
        current_commit = head

    new_branch_path = os.path.join(branches_path, name)
    if os.path.exists(new_branch_path):
        with open(head_path, "w") as head_file:
            head_file.write(f"ref: refs/heads/{name}")
        print(f"{Fore.LIGHTGREEN_EX}Switched to branch {Fore.YELLOW} '{name}'")
        return

    with open(new_branch_path, "w") as branch_file:
        branch_file.write(current_commit)

    with open(head_path, "w") as head_file:
        head_file.write(f"ref: refs/heads/{name}")

    print(
        f"{Fore.LIGHTGREEN_EX}Created and switched to new branch {Fore.YELLOW} '{name}'"
    )


def merge(branch_name):
    repo_path = os.path.join(os.getcwd(), ".Trek")

    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a Trek repository!")
        return

    head_path = os.path.join(repo_path, "HEAD")
    with open(head_path, "r") as head_file:
        head = head_file.read().strip()

    if not head.startswith("ref: "):
        print(f"{Fore.RED}You must be on a branch to merge.")
        return

    current_branch_path = os.path.join(repo_path, head[5:])
    branch_path = os.path.join(repo_path, "refs", "heads", branch_name)

    if not os.path.exists(branch_path):
        print(
            f"{Fore.RED}Branch {Fore.YELLOW}'{branch_name}'{Fore.RED} does not exist."
        )
        return

    # Load commits for both branches
    with open(current_branch_path, "r") as current_branch_file:
        current_commit = current_branch_file.read().strip()

    with open(branch_path, "r") as branch_file:
        branch_commit = branch_file.read().strip()

    if current_commit == branch_commit:
        print(f"{Fore.CYAN}Already up-to-date")
        return

    # Load commit contents
    current_commit_path = os.path.join(repo_path, "objects", current_commit)
    branch_commit_path = os.path.join(repo_path, "objects", branch_commit)

    if not os.path.exists(current_commit_path) or not os.path.exists(
        branch_commit_path
    ):
        print(f"{Fore.RED}Unable to find commit objects. Merge failed.")
        return

    with open(current_commit_path, "r") as current_commit_file:
        current_commit_content = current_commit_file.read()

    with open(branch_commit_path, "r") as branch_commit_file:
        branch_commit_content = branch_commit_file.read()

    # Extract tree hashes from commit contents
    def extract_tree_hash(commit_content):
        for line in commit_content.splitlines():
            if line.startswith("tree "):
                return line.split(" ")[1]
        return None

    current_tree = extract_tree_hash(current_commit_content)
    branch_tree = extract_tree_hash(branch_commit_content)

    # If the trees are identical, no conflicts
    if current_tree == branch_tree:
        with open(current_branch_path, "w") as current_branch_file:
            current_branch_file.write(branch_commit)
        print(
            f"{Fore.LIGHTGREEN_EX}Successfully merged branch {Fore.YELLOW}'{branch_name}'{Fore.LIGHTGREEN_EX} into the current branch (fast-forward)."
        )
        return

    # Conflict scenario
    print(f"{Fore.RED}Merge conflict detected. Resolve conflicts manually.")


def log():
    repo_path = os.path.join(os.getcwd(), ".Trek")

    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a Trek repository!")
        return

    # Read the current branch from HEAD
    head_path = os.path.join(repo_path, "HEAD")
    with open(head_path, "r") as head_file:
        head = head_file.read().strip()

    # If HEAD points to a branch, retrieve the commit hash from the branch file
    current_commit = head
    if head.startswith("ref: "):
        branch_path = os.path.join(repo_path, head[5:])
        with open(branch_path, "r") as branch_file:
            current_commit = branch_file.read().strip()

    prev_commit_hashes = {}
    prev_commit_content = {}

    while current_commit:
        commit_path = os.path.join(repo_path, "objects", current_commit)
        if not os.path.exists(commit_path):
            print(
                f"{Fore.RED}Error: Commit object{Fore.YELLOW} {current_commit}{Fore.RED} does not exist."
            )
            break

        with open(commit_path, "r") as commit_file:
            commit_content = commit_file.read()

        # Get the tree hash from the commit content
        tree_hash = commit_content.split("\n")[0].split(" ")[1]

        # Retrieve the tree object
        tree_path = os.path.join(repo_path, "objects", tree_hash)
        if not os.path.exists(tree_path):
            print(
                f"{Fore.RED}Error: Tree object {Fore.YELLOW} {tree_hash} {Fore.RED}does not exist."
            )
            break

        with open(tree_path, "r") as tree_file:
            tree_content = tree_file.read().strip().split("\n")

        print(f"\n{Fore.CYAN}Commit: {Fore.YELLOW}{current_commit}")
        print(f"{Fore.WHITE}{commit_content}")
        print(f"{Fore.CYAN}Files in this commit:")

        # Store the file hashes for comparison
        current_commit_files = {}

        for line in tree_content:
            file_hash, file_name = line.split(" ")
            current_commit_files[file_name] = file_hash
            print(f"  {Fore.YELLOW}{file_name} {Fore.CYAN}(hash: {file_hash})")

            # Retrieve the file content from the object store
            file_path = os.path.join(repo_path, "objects", file_hash)
            if os.path.exists(file_path):
                with open(file_path, "r") as file:
                    file_content = file.read()
                    print(f"{Fore.CYAN}Content: {Fore.WHITE}{file_content[:30]}")

            # Compare with previous commit (parent) and show changes
            if prev_commit_hashes:
                if file_name in prev_commit_hashes:
                    prev_file_hash = prev_commit_hashes[file_name]
                    prev_file_path = os.path.join(repo_path, "objects", prev_file_hash)

                    if os.path.exists(prev_file_path):
                        with open(prev_file_path, "r") as prev_file:
                            prev_file_content = prev_file.read()

                        # Compare the current file content with the previous file content
                        current_file_path = os.path.join(
                            repo_path, "objects", file_hash
                        )
                        with open(current_file_path, "r") as current_file:
                            current_file_content = current_file.read()

                        # Only show diffs if the file content has changed
                        if prev_file_content != current_file_content:
                            diff = difflib.unified_diff(
                                prev_file_content.splitlines(),
                                current_file_content.splitlines(),
                                fromfile=f"{file_name} (previous)",
                                tofile=f"{file_name} (current)",
                            )

                            print(f"{Fore.MAGENTA}Diff for {file_name}:")
                            for line in diff:
                                if line.startswith("-"):
                                    print(f"{Fore.RED}{line}")
                                elif line.startswith("+"):
                                    print(f"{Fore.LIGHTGREEN_EX}{line}")
                                else:
                                    print(f"{Fore.CYAN}{line}")

                    else:
                        print(
                            f"{Fore.RED}Warning: Previous file {file_name} does not exist in previous commit."
                        )
                else:
                    # The file was added in the current commit
                    print(f"{Fore.LIGHTGREEN_EX}Added file: {file_name}")

            # Check for removed files (in the parent commit but not in the current commit)
            if (
                file_name not in current_commit_files
                and file_name in prev_commit_hashes
            ):
                print(f"{Fore.RED}Removed file: {file_name}")

        prev_commit_hashes = current_commit_files
        prev_commit_content = commit_content

        # Move to the parent commit
        parent_commit = None
        for line in commit_content.split("\n"):
            if line.startswith("parent "):
                parent_commit = line.split(" ")[1]
                break

        current_commit = parent_commit

    print(f"{Fore.CYAN}End of branch history.")


def checkout_branch(branch_name):
    repo_path = os.path.join(os.getcwd(), ".Trek")

    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a Trek repository!")
        return

    branches_path = os.path.join(repo_path, "refs", "heads")
    branch_path = os.path.join(branches_path, branch_name)

    if not os.path.exists(branch_path):
        print(
            f"{Fore.RED}Branch {Fore.YELLOW} '{branch_name}' {Fore.RED} does not exist"
        )
        return

    with open(branch_path, "r") as branch_file:
        commit_hash = branch_file.read().strip()

    # Ensure commit exists
    commit_path = os.path.join(repo_path, "objects", commit_hash)
    if not os.path.exists(commit_path):
        print(
            f"{Fore.RED}Commit {Fore.YELLOW} {commit_hash} {Fore.RED} not found in branch {Fore.CYAN}'{branch_name}'"
        )
        return

    # Simulate updating the working directory (this can be extended)
    print(f"{Fore.CYAN}Switching to branch {Fore.YELLOW} '{branch_name}'...")

    # Update HEAD
    head_path = os.path.join(repo_path, "HEAD")
    with open(head_path, "w") as head_file:
        head_file.write(f"ref: refs/heads/{branch_name}")

    print(f"{Fore.LIGHTGREEN_EX}Checked out branch {Fore.YELLOW} '{branch_name}'.")


# Undo (reset to previous commit)
def reset(commit_hash, hard=False):
    repo_path = os.path.join(os.getcwd(), ".Trek")

    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a Trek repository")
        return

    commit_path = os.path.join(repo_path, "objects", commit_hash)
    if not os.path.exists(commit_path):
        print(f"{Fore.RED}Commit not found")
        return

    with open(commit_path, "r") as commit_file:
        commit_content = commit_file.read()

    # Get the tree hash from the commit
    tree_hash = commit_content.split("\n")[0].split(" ")[1]

    # Retrieve the tree object
    tree_path = os.path.join(repo_path, "objects", tree_hash)
    if not os.path.exists(tree_path):
        print(f"{Fore.RED}Error: Tree object {tree_hash} does not exist.")
        return

    with open(tree_path, "r") as tree_file:
        tree_content = tree_file.read().strip().split("\n")

    # Update the files in the working directory to match the commit
    for line in tree_content:
        file_hash, file_name = line.split(" ")
        file_path = os.path.join(repo_path, "objects", file_hash)

        # Retrieve the file content from the object store
        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                file_content = file.read()

            # Write the content to the working directory
            with open(file_name, "w") as working_file:
                working_file.write(file_content)

    # Update HEAD to the given commit
    head_path = os.path.join(repo_path, "HEAD")
    with open(head_path, "w") as head_file:
        head_file.write(commit_hash)

    if hard:
        print(
            f"{Fore.LIGHTGREEN_EX}Hard reset to commit {Fore.YELLOW}{commit_hash} {Fore.LIGHTGREEN_EX}- Files updated."
        )
    else:
        print(
            f"{Fore.LIGHTGREEN_EX}Soft reset to commit{Fore.YELLOW} {commit_hash} {Fore.LIGHTGREEN_EX}- HEAD updated."
        )


# Simulate pushing a branch to another local branch
def push(source_branch, target_branch):
    """Simulate pushing changes from the source branch to the target branch."""
    repo_path = os.path.join(os.getcwd(), ".Trek")

    # Check if repository exists
    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a Trek repository!")
        return

    # Check if both branches exist
    source_branch_path = os.path.join(repo_path, "refs", "heads", source_branch)
    target_branch_path = os.path.join(repo_path, "refs", "heads", target_branch)

    if not os.path.exists(source_branch_path):
        print(
            f"{Fore.RED}Source branch {Fore.YELLOW}'{source_branch}' {Fore.RED}does not exist."
        )
        return

    if not os.path.exists(target_branch_path):
        print(
            f"{Fore.RED}Target branch {Fore.YELLOW}S'{target_branch}' {Fore.RED}Sdoes not exist."
        )
        return

    # Get the commit hash of the last commit in source branch
    with open(source_branch_path, "r") as source_file:
        last_commit = source_file.read().strip()

    # Push the last commit to the target branch
    with open(target_branch_path, "w") as target_file:
        target_file.write(last_commit)

    print(
        f"{Fore.LIGHTGREEN_EX}Pushed commit from {Fore.YELLOW}'{source_branch}'{Fore.LIGHTGREEN_EX} to {Fore.CYAN}'{target_branch}'."
    )


# Simulate pulling a branch from another local branch
def pull(source_branch, target_branch):
    """Simulate pulling changes from the source branch to the target branch."""
    repo_path = os.path.join(os.getcwd(), ".Trek")

    # Check if repository exists
    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a Trek repository!")
        return

    # Check if both branches exist
    source_branch_path = os.path.join(repo_path, source_branch)
    target_branch_path = os.path.join(repo_path, target_branch)

    if not os.path.exists(source_branch_path):
        print(
            f"{Fore.RED}Source branch {Fore.YELLOW}'{source_branch}' {Fore.RED}does not exist."
        )
        return

    if not os.path.exists(target_branch_path):
        print(
            f"{Fore.RED}Target branch {Fore.YELLOW}'{target_branch}' {Fore.RED}does not exist."
        )
        return

    # Get the commit hash from the source branch
    with open(source_branch_path, "r") as source_file:
        source_commit = source_file.read().strip()

    # Pull the commit into the target branch
    with open(target_branch_path, "w") as target_file:
        target_file.write(source_commit)

    print(
        f"{Fore.LIGHTGREEN_EX}Pulled commit from {Fore.YELLOW}'{source_branch}' {Fore.LIGHTGREEN_EX}into {Fore.CYAN}'{target_branch}'."
    )


def run():
    while True:
        command = input("Trek> ")

        if command == "exit":
            break
        elif command.startswith("init"):
            init()
        elif command.startswith("add "):
            files = command.split()[1:]
            add(files)
        elif command.startswith("commit "):
            message = command[7:]
            commit(message)
        elif command.startswith("branch "):
            branch_name = command.split()[1] if len(command.split()) > 1 else None
            branch(branch_name)
        elif command.startswith("merge "):
            branch_name = command.split()[1]
            merge(branch_name)
        elif command == "log":
            log()
        elif command == "undo":
            undo()
        elif command == "redo":
            redo()
        elif command.startswith("push "):
            branches = command.split()[1:]
            push(branches[0], branches[1])
        elif command.startswith("pull "):
            branches = command.split()[1:]
            pull(branches[0], branches[1])
        elif command.startswith("checkout "):
            branch_name = command.split()[1]
            checkout_branch(branch_name)
        else:
            print(f"{Fore.RED}Unknown Command")


if __name__ == "__main__":
    run()
