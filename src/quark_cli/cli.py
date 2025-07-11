import argparse
import json
import os
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from .api import QuarkAPI

def main():
    parser = argparse.ArgumentParser(description="A CLI tool to interact with Quark Drive.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode.")
    parser.add_argument("--config", default="config.json", help="Path to the configuration file.")
    args = parser.parse_args()

    console = Console()

    try:
        if not os.path.exists(args.config):
            console.print(Panel(f"[bold yellow]Configuration file not found at '{args.config}'.[/]", title="[yellow]Warning[/]", border_style="yellow"))
            cookie = Prompt.ask("[bold cyan]Please enter your Quark Drive cookie[/]")
            target_directory = Prompt.ask("[bold cyan]Please enter the target directory path[/]", default="/")
            config_data = {"cookie": cookie, "target_directory": target_directory}
            with open(args.config, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            console.print(Panel(f"[bold green]Configuration saved to '{args.config}'.[/]", title="[green]Success[/]", border_style="green"))
        else:
            with open(args.config, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            cookie = config_data.get('cookie')
            target_directory = config_data.get('target_directory', '/')

        if not cookie:
            raise ValueError("Cookie is not defined in the configuration file.")

        api = QuarkAPI(cookie=cookie, debug=args.debug)

        should_delete = Confirm.ask("[bold yellow]Do you want to delete the original compressed files after successful processing?[/yellow]", default=False)
        
        api.unzip_all_in_path(target_directory, delete_source_files=should_delete)

    except (ValueError, FileNotFoundError) as e:
        console.print(Panel(f"[bold red]Error:[/] {e}", title="[red]Error[/]", border_style="red"))
    except Exception as e:
        console.print(Panel(f"[bold red]An unexpected error occurred:[/] {e}", title="[red]Error[/]", border_style="red"))

if __name__ == "__main__":
    main()
