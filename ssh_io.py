import os
import paramiko
import pandas as pd
import gzip
import numpy as np
from posydon.grids.termination_flags import get_flag_from_MESA_output

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
    grid_index = original_remote_path.split('/')[-1].split("index_")[-1]

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
        
        return df1, df2, bdf, get_flag_from_MESA_output('quest_mesa_store/{:s}.txt.gz'.format(generic_out_name))

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

        return df1, df2, bdf, get_flag_from_MESA_output('quest_mesa_store/{:s}.txt'.format(generic_out_name))

    # nothing found
    except FileNotFoundError as e:
        ftp_client.close()
        ssh_client.close()

        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), ""
    
def available_comparison(original_remote_paths, alt_parent_dir):

    availability_list = []
    success_list = []

    # open clients
    ssh_client = ssh_connect()
    ftp_client = ssh_client.open_sftp()

    command = 'ls -d {:s}/Zbase_*'.format(alt_parent_dir)
    # execute command and convert stdout
    stdin, stdout, stderr = ssh_client.exec_command(command)
    cmd_out = stdout.read().decode('utf-8').split("\n")

    for mesa_dir in original_remote_paths:
        base_run_dir = mesa_dir.split('/')[-1].split("index_")[0]
        exists = np.array([base_run_dir in alt_dir for alt_dir in cmd_out])
        if any(exists):
            path_to_run = cmd_out[np.where(exists)[0][0]]
            try:
                ftp_client.get(os.path.join(path_to_run, 'out.txt.gz'), 'quest_mesa_store/tmp_out.txt.gz')
                available = True
                
                termination_flag = get_flag_from_MESA_output('quest_mesa_store/tmp_out.txt.gz')
                success = True if (("min_timestep" not in termination_flag) & ("timelimit" not in termination_flag)) else False

            except FileNotFoundError as e:

                try:
                    ftp_client.get(os.path.join(path_to_run, 'out.txt'), 'quest_mesa_store/tmp_out.txt')
                    available = True

                    termination_flag = get_flag_from_MESA_output('quest_mesa_store/tmp_out.txt')
                    success = True if (("min_timestep" not in termination_flag) & ("timelimit" not in termination_flag)) else False

                except FileNotFoundError as e:
                    available = False
                    success = False

            availability_list.append(available)
            success_list.append(success)
        else:
            availability_list.append(False)
            success_list.append(False)

    ftp_client.close()
    ssh_client.close()

    return availability_list, success_list