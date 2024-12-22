import os
import json
import hashlib
from datetime import datetime
import difflib
from colorama import Fore, init

init(autoreset=True)

undo_stack = []
redo_stack = []

"____________________________________Utility Functions____________________________________"


def is_ignored(file_path):
    ignore_path = os.path.join(os.getcwd(), ".trek", ".gitignore")

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
    repo_path = os.path.join(os.getcwd(), ".trek")
    head_path = os.path.join(repo_path, "HEAD")
    with open(head_path, "r") as head_file:
        head = head_file.read().strip()
    if head.startswith("ref: "):
        branch_path = os.path.join(repo_path, head[5:])
        with open(branch_path, "r") as branch_file:
            return branch_file.read().strip()
    return head


"____________________________________Initializes the .trek folder____________________________________"


def init():
    repo_path = os.path.join(os.getcwd(), ".trek")

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


"____________________________________Adds Files to the Staging Area (Index)____________________________________"


def add(files):
    repo_path = os.path.join(os.getcwd(), ".trek")
    index_path = os.path.join(repo_path, "index")

    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a trek repository!")
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
        f"{Fore.LIGHTGREEN_EX}Added {Fore.CYAN} {len(files)} {Fore.LIGHTGREEN_EX} file(s) to the staging area."
    )


"____________________________________Commits (Saves) those Changes____________________________________"


def commit(message):
    repo_path = os.path.join(os.getcwd(), ".trek")
    index_path = os.path.join(repo_path, "index")

    if not os.path.exists(repo_path):
        print(f"{Fore.RED} Not a trek repository")
        return

    if not os.path.exists(index_path):
        print(f"{Fore.RED}Nothing to commit")
        return

    # Loading the staged index
    with open(index_path, "r") as index_file:
        index = json.load(index_file)

    # If the index is empty, nothing to commit
    if not index:
        print(f"{Fore.RED}Nothing to commit")
        return

    # Get the current commit (HEAD) from the repository
    head_path = os.path.join(repo_path, "HEAD")
    with open(head_path, "r") as head_file:
        head = head_file.read().strip()

    parent_commit = None
    if head.startswith("ref: "):  # If HEAD points to a branch
        branch_path = os.path.join(repo_path, head[5:])
        if os.path.exists(branch_path):
            with open(branch_path, "r") as branch_file:
                parent_commit = branch_file.read().strip()

    # Preparing list of files and their hashes
    tree_content = "\n".join(
        [f"{file_hash} {file}" for file, file_hash in index.items()]
    )
    tree_hash = hashlib.sha1(tree_content.encode("utf-8")).hexdigest()
    tree_path = os.path.join(repo_path, "objects", tree_hash)

    if not os.path.exists(tree_path):
        os.makedirs(os.path.dirname(tree_path), exist_ok=True)
        with open(tree_path, "w") as tree_file:
            tree_file.write(tree_content)

    # commit object
    commit_content = f"tree {tree_hash}\n"
    if parent_commit:
        commit_content += f"parent {parent_commit}\n"
    commit_content += f"author User <user@example.com>\n"
    commit_content += (
        f"date {datetime.now().strftime('%a %b %d %H:%M:%S %Y')}\n\n{message}\n"
    )
    commit_hash = hashlib.sha1(commit_content.encode("utf-8")).hexdigest()

    commit_path = os.path.join(repo_path, "objects", commit_hash)
    if not os.path.exists(commit_path):
        os.makedirs(os.path.dirname(commit_path), exist_ok=True)
        with open(commit_path, "w") as commit_file:
            commit_file.write(commit_content)

    # Save the commit in the undo stack
    undo_stack.append(get_current_commit())

    # Update the branch reference to point to the new commit
    if head.startswith("ref: "):
        branch_path = os.path.join(repo_path, head[5:])
        with open(branch_path, "w") as branch_file:
            branch_file.write(commit_hash)
    else:
        with open(head_path, "w") as head_file:
            head_file.write(commit_hash)

    # Clear the index
    with open(index_path, "w") as index_file:
        json.dump({}, index_file)

    print(f"{Fore.YELLOW}[{commit_hash[:7]}] {Fore.CYAN}{message}")


"_______Shows the commit history as well as the changes made in those commits_______"


def log():
    repo_path = os.path.join(os.getcwd(), ".trek")
    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a trek repository!")
        return

    # get current branch from HEAD
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

        # Retrieve the tree object based on the tree hash
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

        current_commit_files = {}

        for line in tree_content:
            file_hash, file_name = line.split(" ")
            current_commit_files[file_name] = file_hash
            print(f"  {Fore.YELLOW}{file_name} {Fore.CYAN}(hash: {file_hash})")

            # Retrieve the file content
            file_path = os.path.join(repo_path, "objects", file_hash)
            if os.path.exists(file_path):
                with open(file_path, "r") as file:
                    file_content = file.read()
                    print(f"{Fore.CYAN}Content: {Fore.WHITE}{file_content[:30]}")

            # Compare with previous commit and show differences
            if prev_commit_hashes:
                if file_name in prev_commit_hashes:
                    prev_file_hash = prev_commit_hashes[file_name]
                    prev_file_path = os.path.join(repo_path, "objects", prev_file_hash)

                    if os.path.exists(prev_file_path):
                        with open(prev_file_path, "r") as prev_file:
                            prev_file_content = prev_file.read()

                        # Compare the content of the current and previous file
                        current_file_path = os.path.join(
                            repo_path, "objects", file_hash
                        )
                        with open(current_file_path, "r") as current_file:
                            current_file_content = current_file.read()

                        # Show diff if contents are different
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
                    print(f"{Fore.LIGHTGREEN_EX}Added file: {file_name}")

            # Check for files that were removed
            if (
                file_name not in current_commit_files
                and file_name in prev_commit_hashes
            ):
                print(f"{Fore.RED}Removed file: {file_name}")

        prev_commit_hashes = current_commit_files

        # Move to the parent commit
        parent_commit = None
        for line in commit_content.split("\n"):
            if line.startswith("parent "):
                parent_commit = line.split(" ")[1]
                break

        current_commit = parent_commit

    print(f"{Fore.CYAN}End of branch history.")


"_______Shows All the Branches and if a Name is Specified, Creates a Branch with that Name and Switches to it_______"


def branch(name=None):
    repo_path = os.path.join(os.getcwd(), ".trek")

    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a trek repository!")
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


"_______Shifts the HEAD to the specified branch_______"


def checkout_branch(branch_name):
    repo_path = os.path.join(os.getcwd(), ".trek")

    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a trek repository!")
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

    print(f"{Fore.CYAN}Switching to branch {Fore.YELLOW} '{branch_name}'...")

    # Updating HEAD
    head_path = os.path.join(repo_path, "HEAD")
    with open(head_path, "w") as head_file:
        head_file.write(f"ref: refs/heads/{branch_name}")

    print(f"{Fore.LIGHTGREEN_EX}Checked out branch {Fore.YELLOW} '{branch_name}'.")


"_______Merges the specified branch into the current branch_______"


def merge(branch_name):
    repo_path = os.path.join(os.getcwd(), ".trek")

    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a trek repository!")
        return

    # current branch from the HEAD file
    head_path = os.path.join(repo_path, "HEAD")
    with open(head_path, "r") as head_file:
        head = head_file.read().strip()

    # make sure that HEAD has a refernce to a branch
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

    with open(current_branch_path, "r") as current_branch_file:
        current_commit = current_branch_file.read().strip()

    with open(branch_path, "r") as branch_file:
        branch_commit = branch_file.read().strip()

    # if both branches already point to the same commit, no merge needed
    if current_commit == branch_commit:
        print(f"{Fore.CYAN}Already up-to-date")
        return

    current_commit_path = os.path.join(repo_path, "objects", current_commit)
    branch_commit_path = os.path.join(repo_path, "objects", branch_commit)

    # if commit objects exist for both commits
    if not os.path.exists(current_commit_path) or not os.path.exists(
        branch_commit_path
    ):
        print(f"{Fore.RED}Unable to find commit objects. Merge failed.")
        return

    # Reading commit contents from both commit objects
    with open(current_commit_path, "r") as current_commit_file:
        current_commit_content = current_commit_file.read()

    with open(branch_commit_path, "r") as branch_commit_file:
        branch_commit_content = branch_commit_file.read()

    # to extract the tree hash from a commit content
    def extract_tree_hash(commit_content):
        for line in commit_content.splitlines():
            if line.startswith("tree "):
                return line.split(" ")[1]
        return None

    # Extract tree hashes from both commit contents
    current_tree = extract_tree_hash(current_commit_content)
    branch_tree = extract_tree_hash(branch_commit_content)

    # If the trees are same then no conflicts and we can merge
    if current_tree == branch_tree:
        with open(current_branch_path, "w") as current_branch_file:
            current_branch_file.write(branch_commit)
        print(
            f"{Fore.LIGHTGREEN_EX}Successfully merged branch {Fore.YELLOW}'{branch_name}'{Fore.LIGHTGREEN_EX} into the current branch (fast-forward)."
        )
        return

    print(f"{Fore.RED}Merge conflict detected. Resolve conflicts manually.")


"_______undo the last commit by resetting to the previous commit_______"


def undo():
    if not undo_stack:
        print(f"{Fore.RED}Nothing to undo.")
        return

    # Pop the last commit from the undo stack (the commit to undo)
    commit_to_undo = undo_stack.pop()

    # Push the current commit onto the redo stack so it can be redone if needed
    redo_stack.append(get_current_commit())

    # Reset the repository to the commit that we want to undo
    reset(commit_to_undo, hard=True)
    print(
        f"{Fore.LIGHTGREEN_EX}Undo successful. Reverted to {Fore.YELLOW}{commit_to_undo}"
    )


"_______redo the last undone commit by resetting to the commit on the redo stack_______"


def redo():
    if not redo_stack:
        print(f"{Fore.RED}Nothing to redo.")
        return

    # Pop the last commit from the redo stack (the commit to redo)
    commit_to_redo = redo_stack.pop()

    # Push the current commit onto the undo stack so it can be undone again if needed
    undo_stack.append(get_current_commit())

    # Reset the repository to the commit that we want to redo
    reset(commit_to_redo, hard=True)
    print(
        f"{Fore.LIGHTGREEN_EX}Redo successful. Reverted to  {Fore.YELLOW}{commit_to_redo}"
    )


"_______Function to reset the repository to a specific commit_______"


def reset(commit_hash, hard=False):
    repo_path = os.path.join(os.getcwd(), ".trek")

    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a trek repository")
        return

    # making the path to the commit object from the given commit hash
    commit_path = os.path.join(repo_path, "objects", commit_hash)

    # Check if the specified commit exists
    if not os.path.exists(commit_path):
        print(f"{Fore.RED}Commit not found")
        return

    # Reading the content of the commit object
    with open(commit_path, "r") as commit_file:
        commit_content = commit_file.read()

    # Extract the tree hash from the commit content (tree hash is saved in the very first line)
    tree_hash = commit_content.split("\n")[0].split(" ")[1]

    # making the path to the tree object corresponding to the tree hash
    tree_path = os.path.join(repo_path, "objects", tree_hash)

    # Check if the tree object exists
    if not os.path.exists(tree_path):
        print(f"{Fore.RED}Error: Tree object {tree_hash} does not exist.")
        return

    # Read the content of the tree object
    with open(tree_path, "r") as tree_file:
        tree_content = tree_file.read().strip().split("\n")

    for line in tree_content:
        file_hash, file_name = line.split(" ")

        # Making the path to the file object in the object store
        file_path = os.path.join(repo_path, "objects", file_hash)

        # retrieving its content
        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                file_content = file.read()

            # Write the content to the file
            with open(file_name, "w") as working_file:
                working_file.write(file_content)

    # Update the HEAD file to point to the specified commit hash
    head_path = os.path.join(repo_path, "HEAD")
    with open(head_path, "w") as head_file:
        head_file.write(commit_hash)

    print(
        f"{Fore.LIGHTGREEN_EX}Hard reset to commit {Fore.YELLOW}{commit_hash} {Fore.LIGHTGREEN_EX}- Files updated."
    )


"_______pushes changes from a source branch to a target branch_______"


def push(source_branch, target_branch):
    # getting the repository path
    repo_path = os.path.join(os.getcwd(), ".trek")

    # Checking if repository exists
    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a trek repository!")
        return

    # making paths for the source and target branch files
    source_branch_path = os.path.join(repo_path, "refs", "heads", source_branch)
    target_branch_path = os.path.join(repo_path, "refs", "heads", target_branch)

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

    # reading the commit hash of the last commit in source branch
    with open(source_branch_path, "r") as source_file:
        last_commit = source_file.read().strip()

    # writing the last commit to the target branch
    with open(target_branch_path, "w") as target_file:
        target_file.write(last_commit)

    print(
        f"{Fore.LIGHTGREEN_EX}Pushed commit from {Fore.YELLOW}'{source_branch}'{Fore.LIGHTGREEN_EX} to {Fore.CYAN}'{target_branch}'."
    )


"_______pulls changes from a source branch to a target branch_______"


def pull(source_branch, target_branch):
    # gets the repository path
    repo_path = os.path.join(os.getcwd(), ".trek")

    # Checking if the repository exist
    if not os.path.exists(repo_path):
        print(f"{Fore.RED}Not a trek repository!")  # Error message
        return

    # making paths for the source and target branch files
    source_branch_path = os.path.join(repo_path, "refs", "heads", source_branch)
    target_branch_path = os.path.join(repo_path, "refs", "heads", target_branch)

    # Check if the source branch exist
    if not os.path.exists(source_branch_path):
        print(
            f"{Fore.RED}Source branch {Fore.YELLOW}'{source_branch}' {Fore.RED}does not exist."
        )
        return

    # Check if the target branch exist
    if not os.path.exists(target_branch_path):
        print(
            f"{Fore.RED}Target branch {Fore.YELLOW}'{target_branch}' {Fore.RED}does not exist."
        )
        return

    # reading commit hash from source branch
    with open(source_branch_path, "r") as source_file:
        source_commit = source_file.read().strip()

    # writing the commit from source in the target branch
    with open(target_branch_path, "w") as target_file:
        target_file.write(source_commit)
    print(
        f"{Fore.LIGHTGREEN_EX}Pulled commit from {Fore.YELLOW}'{source_branch}' {Fore.LIGHTGREEN_EX}into {Fore.CYAN}'{target_branch}'."
    )


def run():
    while True:
        command = input("trek> ")

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
        elif command == "log":
            log()
        elif command.startswith("branch "):
            branch_name = command.split()[1] if len(command.split()) > 1 else None
            branch(branch_name)
        elif command.startswith("checkout "):
            branch_name = command.split()[1]
            checkout_branch(branch_name)
        elif command.startswith("merge "):
            branch_name = command.split()[1]
            merge(branch_name)
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
        else:
            print(f"{Fore.RED}Unknown Command")


if __name__ == "__main__":
    run()
