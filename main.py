import os
import time
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
import pdfplumber
import shutil
import subprocess
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_groq import ChatGroq

@tool
def convert_bytes(bytes):
    """
    Convert bytes between units of measurement

    Args:
        bytes (int): The number of bytes to convert
    """
    for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024

@tool
def make_dir(path):
    """
    Make a directory

    Args:
        path (str): The path of the directory to be created including the name of the directory
    """
    try:
        if not os.path.exists(path):
            os.mkdir(path)
        else:
            print("Directory already exists")
    except Exception as e:
        print("Error creating directory:", e)

@tool
def make_file(path,content):
    """
    Create a file at the specified path with the given content.
    
    Args:
    path (str): The path to the file to create including the file name.
    content (str): The content to write to the file.
    """
    try:
        with open(path, "w") as f:
            f.write(content) if content else ""
            f.close()
    except Exception as e:
        print("Error creating file:", e)

def find_file(filename,path):
    coincidences = []
    for root, dirs, files in os.walk(path):
        if filename in files:
            coincidences.append(os.path.join(root, filename))

    if len(coincidences) == 0:
        print("No coincidences found")
    else:
        print("Coincidences found:")
        for file in coincidences:
            print(file)

@tool
def move_file(path_origin, path_final):
    """
    Moves a file or folder from the origin path to the final path

    Args:
        path_origin (str): The initial path of the file or folder
        path_final (str): The destination path of the file or folder (it does not include the name of the element that is moving)
    """
    if os.path.exists(path_final):
        try:
            shutil.move(path_origin, path_final)
        except Exception as e:
            print("Error moving file:", e)
    else:
        print("Final path does not exist, you must create it first")

def count_size_file(path):
    size = os.path.getsize(path)
    return convert_bytes(size)

@tool
def count_size_dir(path):
    """
    Counts the size of a directory recursively

    Args:
        path (str): The path to the directory
    """
    for root, dirs, files in os.walk(path):
        size = sum(os.path.getsize(os.path.join(root, name)) for name in files)
    return convert_bytes(size)

@tool
def run_command(command):
    """
    Executes a command in the terminal

    Args:
        command (str): The command to be executed
    """
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    print(stdout.decode())
    print(stderr.decode())

def search_in_pdf(path,chain):
    with pdfplumber.open(path) as f:
        for page in f.pages[:100]:
            response = chain.invoke({"file_content": page.extract_text()[:3000]})
            if response.content == "True":
                return(path)
            return f"{path}: False"

def search_in_file(file,path,chain,filters):
    if filters:
        if any(file.endswith(termination) for termination in filters):
            response = chain.invoke({"file_content": open(path,encoding="utf-8").read()[:3000]})
            if response.content == "True":
                return(path)
            return f"file {file}: False"         
    else:
        if any(file.endswith(termination) for termination in [".txt",".py",".c"]):
            response = chain.invoke({"file_content": open(path,encoding="utf-8").read()[:3000]})
            if response.content == "True":
                return(path)
            return f"file {file}: False"

@tool
def search_file_by_content(content,path,filters,ignore_dependencies=True):
    """
    Searches for files in the path that are related to the specified content.

    Args:
        content (str): The content to search for.
        path (str): The path to search in.
        filters (list): A list of file extensions to filter the search by. They should include the dot (.). If there are noo filters, the argument must be passed as None.
        ignore_dependencies (bool): Whether to ignore dependencies folders when searching for files. Defaults to True.
    """
    system = f"Your role is to analyze the prompt text and return 'True' if it is related to the following concept: <START_OF_CONCEPT>{content}<END_OF_CONCEPT> or 'False' if it is not. Only answer with True or False and only answer with True if you are completely sure about it."
    analizer = ChatOllama(temperature=0, model="llama3.1:8b")
    human = "{file_content}"
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    chain = prompt | analizer

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=os.cpu_count() * 5) as executor:
        futures = []
        for root, directories, files in os.walk(path):
            directories[:] = [d for d in directories if not d.startswith(".")]
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if filters:
                        if any(file.endswith(termination) for termination in filters):
                            if file.endswith(".pdf"):
                                try:
                                    futures.append(executor.submit(search_in_pdf,file_path,chain,))
                                except:
                                    pass
                            else:
                                futures.append(executor.submit(search_in_file,file,file_path,chain,filters))
                    else:
                        if file.endswith(".pdf"):
                            try:
                                futures.append(executor.submit(search_in_pdf,file_path,chain))
                            except:
                                pass
                        elif any(file.endswith(termination) for termination in [".txt",".py",".c"]):
                            futures.append(executor.submit(search_in_file,file,file_path,chain,filters))
                except:
                    pass
        for future in as_completed(futures):
            print(future.result())
        end_time = time.time()
        runtime = end_time - start_time
        print(f"Time taken: {runtime:.2f} seconds")

def main():
    #make_dir("C:\\Users\\irecg\\OneDrive\\Escritorio\\test_dir")
    #make_file("C:\\Users\\irecg\\OneDrive\\Escritorio\\test_dir\\test.txt",str(["test" for i in range(1000)]))
    #move_file("C:\\Users\\irecg\\OneDrive\\Escritorio\\test_dir\\test.py", "C:\\Users\\irecg\\OneDrive\\Escritorio\\test_dir2\\test.py")
    #dir_size = count_size_dir("C:\\Users\\irecg\\OneDrive\\Escritorio\\test_dir")
    #search_file_by_content("main","C:\\Users\\irecg",filters=['.py'])
    #response = ollama.chat(model="llama3.1",messages=[
        #{"role": "system", "content": "You are a helpful assistant. You are able to convert bytes to KB, MB, GB, TB. using the convert_bytes function."},
        #{"role": "user", 
        #"content": "How many KB are 2GB?"},
    #])
    #print(response["message"]["content"])
    system = "You are a helpful assistant. Use the tools that you have available when you need it. Tools: convert_bytes,make_dir,run_command,count_size_dir,move_file,make_file,search_file_by_content. Keep in mind that you are running on a Windows machine."
    human = "{text}"
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    chat = ChatGroq(temperature=0, model="llama-3.3-70b-versatile").bind_tools(tools=[convert_bytes,make_dir,run_command,count_size_dir,move_file,make_file,search_file_by_content])

    chain = prompt | chat
    input_text = input("Prompt: ")
    response = chain.invoke({"text": input_text})
    print(response.tool_calls)
    proceed = input("Proceed? (y/n)")
    if proceed.lower() == "y":
        for tool_call in response.tool_calls:
            selected_tool = {"convert_bytes": convert_bytes, "make_dir": make_dir, "run_command": run_command, "count_size_dir": count_size_dir, "move_file": move_file, "make_file": make_file, "search_file_by_content": search_file_by_content}[tool_call["name"].lower()]
            selected_tool.invoke(tool_call)
    else:
        print("Exiting...")
        
    

if __name__ == "__main__":
    main()  