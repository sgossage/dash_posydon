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

def download_data_to_df(original_remote_path, alt_parent_dir=None):

    # open clients
    ssh_client = ssh_connect()
    ftp_client = ssh_client.open_sftp()

    # (remote) parent dir of directory stored in grid and base run name (w/o grid index)
    parent_dir = "/" + os.path.join(*original_remote_path.split('/')[:-1])
    base_run_dir = original_remote_path.split('/')[-1].split("index_")[0]

    if alt_parent_dir is None:
        # command to list base run dir in parent dir
        command = 'ls -d {:s}/{:s}*'.format(parent_dir, base_run_dir)
        generic_h1_name = "history1"
        generic_h2_name = "history2"
        generic_bh_name = "binary_history"
        generic_out_name = "out"
    else:
        # command to list base run dir in alternate parent dir for comparison
        command = 'ls -d {:s}/{:s}*'.format(alt_parent_dir, base_run_dir)
        generic_h1_name = "alt_history1"
        generic_h2_name = "alt_history2"
        generic_bh_name = "alt_binary_history"
        generic_out_name = "alt_out"

    # execute command and convert stdout
    stdin, stdout, stderr = ssh_client.exec_command(command)
    cmd_out = stdout.read().decode('utf-8').strip("\n")
    # this is the path to the desired run
    path_to_run = cmd_out
    
    # try to download history files and console output from the run
    try:
        ftp_client.get(os.path.join(path_to_run, 'LOGS1/history.data.gz'), 'quest_mesa_store/{:s}.data.gz'.format(generic_h1_name))
        ftp_client.get(os.path.join(path_to_run, 'LOGS2/history.data.gz'), 'quest_mesa_store/{:s}.data.gz'.format(generic_h2_name))
        ftp_client.get(os.path.join(path_to_run, 'binary_history.data.gz'), 'quest_mesa_store/{:s}.data.gz'.format(generic_bh_name))
        ftp_client.get(os.path.join(path_to_run, 'out.txt.gz'), 'quest_mesa_store/{:s}.txt.gz'.format(generic_out_name))

        ftp_client.close()
        ssh_client.close()

        df1 = pd.read_csv("quest_mesa_store/{:s}.data.gz".format(generic_h1_name), header=4, delimiter=r"\s+")
        df2 = pd.read_csv("quest_mesa_store/{:s}.data.gz".format(generic_h2_name), header=4, delimiter=r"\s+")
        bdf = pd.read_csv("quest_mesa_store/{:s}.data.gz".format(generic_bh_name), header=4, delimiter=r"\s+")

        return df1, df2, bdf, check_termcode_gz('quest_mesa_store/{:s}.txt.gz'.format(generic_out_name))

    except FileNotFoundError as e:
        pass

    # if no gzipped files found, try looking for uncompressed
    try:
        ftp_client.get(os.path.join(path_to_run, 'LOGS1/history.data'), 'quest_mesa_store/{:s}.data'.format(generic_h1_name))
        ftp_client.get(os.path.join(path_to_run, 'LOGS2/history.data'), 'quest_mesa_store/{:s}.data'.format(generic_h2_name))
        ftp_client.get(os.path.join(path_to_run, 'binary_history.data'), 'quest_mesa_store/{:s}.data'.format(generic_bh_name))
        ftp_client.get(os.path.join(path_to_run, 'out.txt'), 'quest_mesa_store/{:s}.txt'.format(generic_out_name))

        ftp_client.close()
        ssh_client.close()

        df1 = pd.read_csv("quest_mesa_store/{:s}.data".format(generic_h1_name), header=4, delimiter=r"\s+")
        df2 = pd.read_csv("quest_mesa_store/{:s}.data".format(generic_h2_name), header=4, delimiter=r"\s+")
        bdf = pd.read_csv("quest_mesa_store/{:s}.data".format(generic_bh_name), header=4, delimiter=r"\s+")

        return df1, df2, bdf, check_termcode('quest_mesa_store/{:s}.txt'.format(generic_out_name))

    # nothing found
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
    