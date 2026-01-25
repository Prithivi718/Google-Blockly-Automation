import json

def load_queue(file_name):
    try:
        with open(file_name, 'r') as file:
            data = json.load(file)
        queue = json.dumps(data, indent=4)
        print("File data =", queue)
        file.close()
        return data

    except FileNotFoundError:
        print(f"Error: The file {file_name} was not found.")


def get_next_pending(queue):

    for index, problem in enumerate(queue):
        if problem['status'] == "PENDING":
            return index, problem

if __name__ == "__main__":
    queue= load_queue('queue.json')
    index, problem= get_next_pending(queue)
    pid = problem['problem_id']
    statement = problem['statement']
    print(f"Problem ID: {pid}\nProblem Statement: {statement}")