import os
import paramiko
import pandas as pd
import gzip

def ssh_connect():
    
    with open("config.ini", 'r') as configf:
        config_lines = configf.readlines()

    hn = config_lines[0].strip("\n")
    un = config_lines[1].strip("\n")
    pw = config_lines[2].strip("\n")

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=hn,username=un,password=pw)

    return ssh_client

def download_data_to_df(remote_path):
    ssh_client = ssh_connect()
    ftp_client=ssh_client.open_sftp()

    parent_dir = "/" + os.path.join(*remote_path.split('/')[:-1])
    base_run_dir = remote_path.split('/')[-1].split("index_")[0]

    command = 'ls -d {:s}/{:s}*'.format(parent_dir, base_run_dir)
    stdin, stdout, stderr = ssh_client.exec_command(command)
    cmd_out = stdout.read().decode('utf-8').strip("\n")
    path_to_run = cmd_out
    
    try:
        ftp_client.get(os.path.join(path_to_run, 'LOGS1/history.data.gz'), 'quest_mesa_store/alt_history1.data.gz')
        ftp_client.get(os.path.join(path_to_run, 'LOGS2/history.data.gz'), 'quest_mesa_store/alt_history2.data.gz')
        ftp_client.get(os.path.join(path_to_run, 'binary_history.data.gz'), 'quest_mesa_store/alt_binary_history.data.gz')
        ftp_client.get(os.path.join(path_to_run, 'out.txt.gz'), 'quest_mesa_store/alt_out.txt.gz')

        ftp_client.close()
        ssh_client.close()

        df1 = pd.read_csv("quest_mesa_store/alt_history1.data.gz", header=4, delimiter=r"\s+")
        df2 = pd.read_csv("quest_mesa_store/alt_history2.data.gz", header=4, delimiter=r"\s+")
        bdf = pd.read_csv("quest_mesa_store/alt_binary_history.data.gz", header=4, delimiter=r"\s+")

        return df1, df2, bdf

    except FileNotFoundError as e:
        pass

    try:
        ftp_client.get(os.path.join(path_to_run, 'LOGS1/history.data'), 'quest_mesa_store/alt_history1.data')
        ftp_client.get(os.path.join(path_to_run, 'LOGS2/history.data'), 'quest_mesa_store/alt_history2.data')
        ftp_client.get(os.path.join(path_to_run, 'binary_history.data'), 'quest_mesa_store/alt_binary_history.data')
        ftp_client.get(os.path.join(path_to_run, 'out.txt'), 'quest_mesa_store/alt_out.txt')

        ftp_client.close()
        ssh_client.close()

        df1 = pd.read_csv("quest_mesa_store/alt_history1.data", header=4, delimiter=r"\s+")
        df2 = pd.read_csv("quest_mesa_store/alt_history2.data", header=4, delimiter=r"\s+")
        bdf = pd.read_csv("quest_mesa_store/alt_binary_history.data", header=4, delimiter=r"\s+")

        return df1, df2, bdf

    except FileNotFoundError as e:
        ftp_client.close()
        ssh_client.close()

        return None, None, None
    
    

def get_comparison_data(remote_mesa_dir, remote_compare_dir):

    ssh_client = ssh_connect()
    ftp_client=ssh_client.open_sftp()

    base_run_dir = remote_mesa_dir.split('/')[-1].split("index_")[0]

    command = 'ls -d {:s}/{:s}*'.format(remote_compare_dir, base_run_dir)
    stdin, stdout, stderr = ssh_client.exec_command(command)
    cmd_out = stdout.read().decode('utf-8').strip("\n")
    path_to_run = cmd_out
    
    try:
        ftp_client.get(os.path.join(path_to_run, 'LOGS1/history.data.gz'), 'quest_mesa_store/alt_history1.data.gz')
        ftp_client.get(os.path.join(path_to_run, 'LOGS2/history.data.gz'), 'quest_mesa_store/alt_history2.data.gz')
        ftp_client.get(os.path.join(path_to_run, 'binary_history.data.gz'), 'quest_mesa_store/alt_binary_history.data.gz')
        ftp_client.get(os.path.join(path_to_run, 'out.txt.gz'), 'quest_mesa_store/alt_out.txt.gz')

        ftp_client.close()
        ssh_client.close()

        df1 = pd.read_csv("quest_mesa_store/alt_history1.data.gz", header=4, delimiter=r"\s+")
        df2 = pd.read_csv("quest_mesa_store/alt_history2.data.gz", header=4, delimiter=r"\s+")
        bdf = pd.read_csv("quest_mesa_store/alt_binary_history.data.gz", header=4, delimiter=r"\s+")

        return df1, df2, bdf, check_termcode_gz('quest_mesa_store/alt_out.txt.gz')

    except FileNotFoundError as e:
        pass

    try:
        ftp_client.get(os.path.join(path_to_run, 'LOGS1/history.data'), 'quest_mesa_store/alt_history1.data')
        ftp_client.get(os.path.join(path_to_run, 'LOGS2/history.data'), 'quest_mesa_store/alt_history2.data')
        ftp_client.get(os.path.join(path_to_run, 'binary_history.data'), 'quest_mesa_store/alt_binary_history.data')
        ftp_client.get(os.path.join(path_to_run, 'out.txt'), 'quest_mesa_store/alt_out.txt')

        ftp_client.close()
        ssh_client.close()

        df1 = pd.read_csv("quest_mesa_store/alt_history1.data", header=4, delimiter=r"\s+")
        df2 = pd.read_csv("quest_mesa_store/alt_history2.data", header=4, delimiter=r"\s+")
        bdf = pd.read_csv("quest_mesa_store/alt_binary_history.data", header=4, delimiter=r"\s+")

        return df1, df2, bdf, check_termcode('quest_mesa_store/alt_out.txt')

    except FileNotFoundError as e:
        ftp_client.close()
        ssh_client.close()

        return None, None, None, None
    

def check_termcode(file_name, simple=False):
    
    # check out.txt
    with open(file_name, 'r') as openf:
        
        lines = openf.readlines()
        
        for line in lines[::-1]:    
            if "termination" in line:
                if "Both stars" in line:
                    if simple:
                        return True
                    else:
                        return "Both stars RLOF"
                elif "overflow from L2" in line:
                    if simple:
                        return True
                    else:
                        return "L2 RLOF"
                elif "L2 overflow during case A" in line:
                    if simple:
                        return True
                    else:
                        return "Case A L2 RLOF"
                elif "maximum mass transfer rate" in line:
                    if simple:
                        return True
                    else:
                        return "Max MT rate"
                else:
                    if simple:
                        return True
                    else:
                        return line.split("code: ")[-1].strip('\n')

    """ 
    #print("No termination code found in out.txt")
    run_index = file_name.split("_")[-1]
    
    
    parent_path = os.path.dirname(file_name)
    mesa_grid_files = glob(parent_path + "/mesa_grid.*")
    
    for mesa_grid_fn in mesa_grid_files:
        if run_index in mesa_grid_fn:
            with open(mesa_grid_fn, "r") as openf:
                lines = openf.readlines()
                
            break
    
    if "TIME LIMIT" in "".join(lines):
        if simple:
            return False
        else:
            return "CPU Wall Time"
    elif "Segmentation fault" in "".join(lines):
        if simple:
            return False
        else:
            return "Segmentation fault"
    #elif "No such file or directory" in "".join(lines):
    #    if simple:
    #        return False
    #    else:
            #return "rm: cannot remove \'LOGS*/profile*\': No such file or directory"
    #        return "File I/O error"
    """
    if simple:
        return False
    else:
        return "Unknown"

def check_termcode_gz(file_name, simple=False):
    
    # check out.txt
    with gzip.open(file_name, 'rt') as openf:
        
        lines = openf.readlines()
        
        for line in lines[::-1]:    
            if "termination" in line:
                if "Both stars" in line:
                    if simple:
                        return True
                    else:
                        return "Both stars RLOF"
                elif "overflow from L2" in line:
                    if simple:
                        return True
                    else:
                        return "L2 RLOF"
                elif "L2 overflow during case A" in line:
                    if simple:
                        return True
                    else:
                        return "Case A L2 RLOF"
                elif "maximum mass transfer rate" in line:
                    if simple:
                        return True
                    else:
                        return "Max MT rate"
                else:
                    if simple:
                        return True
                    else:
                        return line.split("code: ")[-1].strip('\n')
                    
    return "CPU Wall Time"
    
    """
    #print("No termination code found in out.txt")
    run_index = file_name.split("_")[-1]
    
    
    parent_path = os.path.dirname(file_name)
    mesa_grid_files = glob(parent_path + "/mesa_grid.*")
    
    for mesa_grid_fn in mesa_grid_files:
        if run_index in mesa_grid_fn:
            with open(mesa_grid_fn, "r") as openf:
                lines = openf.readlines()
                
            break
    
    if "TIME LIMIT" in "".join(lines):
        if simple:
            return False
        else:
            return "CPU Wall Time"
    elif "Segmentation fault" in "".join(lines):
        if simple:
            return False
        else:
            return "Segmentation fault"
    #elif "No such file or directory" in "".join(lines):
    #    if simple:
    #        return False
    #    else:
            #return "rm: cannot remove \'LOGS*/profile*\': No such file or directory"
    #        return "File I/O error"
    """
    if simple:
        return False
    else:
        return "Unknown"
    