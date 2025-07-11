import requests
import json
import time
import os
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, MofNCompleteColumn

class QuarkAPI:
    """
    A class to interact with the Quark Drive API for unzipping, organizing, and cleaning files.
    It uses the rich library for enhanced output and automatically retries failed tasks.
    """

    def __init__(self, cookie: str, debug: bool = False):
        self.console = Console()
        self.debug = debug
        self.session = requests.Session()
        
        self.console.print(Panel("[bold cyan]Quark API Initializing...[/]", title="[yellow]Status[/]", border_style="green"))
        
        self.session.headers['Cookie'] = cookie
        if not self.session.headers['Cookie']:
            raise ValueError("Cookie is missing or empty.")

        self._log_debug("QuarkAPI initialized successfully with the provided cookie.")

    def _log_debug(self, message: str):
        if self.debug:
            self.console.print(f"[bold yellow]DEBUG:[/] {message}")

    def _make_request(self, method: str, url: str, **kwargs) -> dict:
        base_params = {'pr': 'ucpro', 'fr': 'pc', 'uc_param_str': ''}
        final_params = base_params.copy()
        if 'params' in kwargs:
            final_params.update(kwargs.pop('params', {}))

        full_url = f"https://drive-pc.quark.cn/1/clouddrive{url}"
        
        request_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd', 'Cache-Control': 'no-cache', 'Pragma': 'no-cache',
            'Origin': 'https://pan.quark.cn', 'Referer': 'https://pan.quark.cn/',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"', 'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"', 'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site', 'priority': 'u=1, i', 'Cookie': self.session.headers.get('Cookie')
        }

        if 'data' in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])
            request_headers['Content-Type'] = 'application/json;charset=UTF-8'

        self._log_debug(f"Request -> {method} {full_url}")
        if self.debug:
            try:
                parsed_json = json.loads(json.dumps(request_headers))
                pretty_response = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                self.console.print(Syntax(pretty_response, "json", theme="monokai", line_numbers=True))
            except json.JSONDecodeError:
                self.console.print(f"[yellow]Request headers are not valid JSON, printing raw:[/]\n{request_headers}")

        response = self.session.request(method, full_url, headers=request_headers, params=final_params, **kwargs)
        
        self._log_debug(f"Response <- Status Code: {response.status_code}")
        if self.debug:
            try:
                parsed_json = json.loads(response.text)
                pretty_response = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                self.console.print(Syntax(pretty_response, "json", theme="monokai", line_numbers=True))
            except json.JSONDecodeError:
                self.console.print(f"[yellow]Response is not valid JSON, printing raw:[/]\n{response.text}")

        if response.status_code != 200:
            raise requests.HTTPError(f"Request failed: {response.status_code}, URL: {full_url}")
        
        data = response.json()
        if data.get("code") != 0 and data.get("status") != 0:
            raise Exception(f"API returned a business error: {data.get('message') or response.text}")
        return data

    def get_files_by_pid(self, p_fid: str) -> list:
        self._log_debug(f"Fetching file list for parent ID: '{p_fid}'...")
        params = {'pdir_fid': p_fid, '_page': 1, '_size': 500, '_sort': 'file_type:asc,updated_at:desc'}
        data = self._make_request("GET", "/file/sort", params=params)
        return data.get("data", {}).get("list", [])

    def move_files(self, file_fids: list[str], to_pdir_fid: str):
        payload = {"action_type": 1, "to_pdir_fid": to_pdir_fid, "filelist": file_fids, "exclude_fids": []}
        self._make_request("POST", "/file/move", data=payload)

    def delete_items(self, item_fids: list[str]):
        payload = {"action_type": 2, "filelist": item_fids, "exclude_fids": []}
        self._make_request("POST", "/file/delete", data=payload)

    def get_fid_by_path(self, path: str) -> str:
        self._log_debug(f"Starting path resolution for: '{path}'")
        if path == '/': return "0"
        path_parts = [part for part in path.strip().split('/') if part]
        current_fid = "0"

        for part in path_parts:
            files_in_dir = self.get_files_by_pid(current_fid)
            found = False
            for item in files_in_dir:
                if item.get("file_name") == part:
                    current_fid = item["fid"]
                    found = True
                    break
            if not found:
                raise FileNotFoundError(f"Could not find '{part}' in path '{path}'.")
        
        self.console.print(f"[bold magenta]Path resolved successfully:[/] FID for '{path}' is [bold green]{current_fid}[/]")
        return current_fid

    def _unzip_task(self, files_to_process: list, target_dir_fid: str, delay: float, description: str) -> tuple[list, list]:
        successfully_unzipped, failed_to_unzip = [], []
        progress_columns = [TextColumn("[progress.description]{task.description}"), BarColumn(), MofNCompleteColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TimeRemainingColumn()]
        
        with Progress(*progress_columns, console=self.console) as progress:
            task = progress.add_task(f"[cyan]{description}[/]", total=len(files_to_process))
            for file_info in files_to_process:
                file_name, file_id = file_info["file_name"], file_info["fid"]
                progress.log(f"  -> [cyan]Requesting unzip for:[/] {file_name}")
                payload = {"fid": file_id, "pwd": "", "select_mode": 2, "path_no_list": [1], "curr_path_no": 0, "remember_pwd": False, "conflict_mode": 3, "suffix_type": 0, "to_pdir_fid": target_dir_fid}
                try:
                    self._make_request("POST", "/archive/unarchive", data=payload)
                    progress.log(f"     [bold green]✅ Unzip request successful:[/] {file_name}")
                    successfully_unzipped.append(file_info)
                except Exception as e:
                    progress.log(f"     [bold red]❌ Unzip request failed:[/] {file_name}. Reason: {e}")
                    failed_to_unzip.append(file_info)
                progress.update(task, advance=1)
                time.sleep(delay)
        return successfully_unzipped, failed_to_unzip

    def _organize_task(self, files_to_process: list, target_dir_fid: str, delay: float, description: str) -> tuple[list, list]:
        organized_folders, failed_to_organize = [], []
        progress_columns = [TextColumn("[progress.description]{task.description}"), BarColumn(), MofNCompleteColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TimeRemainingColumn()]
        
        self.console.print("[cyan]Refreshing directory to find newly created folders...[/]")
        all_files_in_dir = self.get_files_by_pid(target_dir_fid)

        with Progress(*progress_columns, console=self.console) as progress:
            task = progress.add_task(f"[cyan]{description}[/]", total=len(files_to_process))
            for file_info in files_to_process:
                file_name = file_info["file_name"]
                progress.log(f"  -> [cyan]Organizing:[/] {file_name}")
                try:
                    unzipped_folder_name = os.path.splitext(file_name)[0]
                    new_folder_fid = None
                    for item in all_files_in_dir:
                        if item.get("file_name") == unzipped_folder_name and item.get("dir"):
                            new_folder_fid = item["fid"]
                            break
                    
                    if new_folder_fid:
                        progress.log(f"     [green]Found new folder, preparing to move contents...[/]")
                        files_to_move = self.get_files_by_pid(new_folder_fid)
                        if files_to_move:
                            fids_to_move = [item['fid'] for item in files_to_move]
                            self.move_files(fids_to_move, target_dir_fid)
                            progress.log("     [bold green]✅ Files moved successfully![/]")
                        else:
                            progress.log("     [yellow]New folder is empty, no move needed.[/]")
                        organized_folders.append({"file_name": unzipped_folder_name, "fid": new_folder_fid})
                    else:
                        progress.log(f"     [yellow]Warning: Could not find a matching unzipped folder, skipping move.[/]")
                except Exception as e:
                    progress.log(f"     [bold red]❌ Organization failed:[/] {file_name}. Reason: {e}")
                    failed_to_organize.append(file_info)
                progress.update(task, advance=1)
                time.sleep(delay)
        return organized_folders, failed_to_organize

    def _cleanup_task(self, folders_to_delete: list, delay: float, description: str) -> list:
        failed_to_delete = []
        progress_columns = [TextColumn("[progress.description]{task.description}"), BarColumn(), MofNCompleteColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TimeRemainingColumn()]
        
        with Progress(*progress_columns, console=self.console) as progress:
            task = progress.add_task(f"[cyan]{description}[/]", total=len(folders_to_delete))
            for folder_info in folders_to_delete:
                folder_name, folder_id = folder_info["file_name"], folder_info["fid"]
                progress.log(f"  -> [cyan]Requesting deletion of empty folder:[/] {folder_name}")
                try:
                    self.delete_items([folder_id])
                    progress.log(f"     [bold green]✅ Deletion successful:[/] {folder_name}")
                except Exception as e:
                    progress.log(f"     [bold red]❌ Deletion failed:[/] {folder_name}. Reason: {e}")
                    failed_to_delete.append(folder_info)
                progress.update(task, advance=1)
                time.sleep(delay)
        return failed_to_delete

    def unzip_all_in_path(self, dir_path: str, delete_source_files: bool):
        self.console.print(f"[cyan]Processing path:[/] {dir_path}")
        try:
            target_dir_fid = self.get_fid_by_path(dir_path)
            all_compressed_files = [f for f in self.get_files_by_pid(target_dir_fid) if not f.get("dir") and f.get("file_name", "").split('.')[-1] in ['zip', 'rar', '7z', 'tar', 'gz']]

            if not all_compressed_files:
                self.console.print("[yellow]No supported compressed files found.[/]")
                return

            # --- Task 1: Unzip ---
            self.console.print(Panel(f"[bold cyan]Task 1: Unzipping {len(all_compressed_files)} files[/]", title="[yellow]Stage[/]", border_style="blue"))
            successful_unzip, failed_unzip = self._unzip_task(all_compressed_files, target_dir_fid, 0.2, "Unzipping...")
            if failed_unzip:
                self.console.print(Panel("\n".join([f"- {f['file_name']}" for f in failed_unzip]), title="[bold red]Unzip Failure Report[/]", border_style="red"))
                s_unzip_retry, _ = self._unzip_task(failed_unzip, target_dir_fid, 0.8, "Retrying unzips...")
                successful_unzip.extend(s_unzip_retry)

            if not successful_unzip:
                self.console.print("[yellow]No files were successfully unzipped, aborting.[/]")
                return

            # --- Task 2: Organize ---
            self.console.print(Panel(f"[bold cyan]Task 2: Organizing {len(successful_unzip)} folders[/]", title="[yellow]Stage[/]", border_style="blue"))
            self.console.print("[yellow]Waiting for server to process... (5 seconds)[/]")
            time.sleep(5)
            organized_folders, failed_organize = self._organize_task(successful_unzip, target_dir_fid, 0.2, "Organizing...")
            if failed_organize:
                self.console.print(Panel("\n".join([f"- {f['file_name']}" for f in failed_organize]), title="[bold red]Organization Failure Report[/]", border_style="red"))
                o_folders_retry, _ = self._organize_task(failed_organize, target_dir_fid, 0.8, "Retrying organization...")
                organized_folders.extend(o_folders_retry)

            # --- Task 3: Clean up empty folders ---
            if organized_folders:
                self.console.print(Panel(f"[bold cyan]Task 3: Cleaning up {len(organized_folders)} empty folders[/]", title="[yellow]Stage[/]", border_style="blue"))
                failed_delete = self._cleanup_task(organized_folders, 0.2, "Cleaning...")
                if failed_delete:
                    self.console.print(Panel("\n".join([f"- {f['file_name']}" for f in failed_delete]), title="[bold red]Cleanup Failure Report[/]", border_style="red"))
                    self._cleanup_task(failed_delete, 0.8, "Retrying cleanup...")
            
            # --- Task 4: Clean up source files ---
            if delete_source_files:
                self.console.print(Panel(f"[bold cyan]Task 4: Cleaning up {len(successful_unzip)} source archives[/]", title="[yellow]Stage[/]", border_style="blue"))
                failed_delete_source = self._cleanup_task(successful_unzip, 0.2, "Cleaning up source files...")
                if failed_delete_source:
                    self.console.print(Panel("\n".join([f"- {f['file_name']}" for f in failed_delete_source]), title="[bold red]Source File Cleanup Failure Report[/]", border_style="red"))
                    self._cleanup_task(failed_delete_source, 0.8, "Retrying source cleanup...")

            self.console.print(Panel("[bold green]All tasks completed![/]", title="[yellow]Status[/]", border_style="green"))

        except (ValueError, FileNotFoundError) as e:
            self.console.print(Panel(f"[bold red]Initialization or configuration error:[/] {e}", title="[red]Error[/]", border_style="red"))
        except Exception as e:
            self.console.print(Panel(f"[bold red]An unknown critical error occurred:[/] {e}", title="[red]Error[/]", border_style="red"))
