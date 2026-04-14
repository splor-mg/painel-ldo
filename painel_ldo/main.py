from dotenv import load_dotenv
import argparse
import subprocess
from databases import carrega_trata_dados, cria_base_receita_fonte_analise, build_toml

load_dotenv()

def build_command():
    valor_painel = carrega_trata_dados()
    cria_base_receita_fonte_analise(valor_painel=valor_painel, tipo_base='receita')
    cria_base_receita_fonte_analise(valor_painel=valor_painel, tipo_base='fonte')


def extract_command():
    try:
        subprocess.run(['dpm', 'install'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running 'dpm install': {e}")
        exit(1)
    except FileNotFoundError:
        print("Error: 'dpm' command not found. Please ensure it is installed and in your PATH.")
        exit(1)


def main():
    parser = argparse.ArgumentParser(description='LDO Panel data processing tool')
    parser.add_argument('command', choices=['toml', 'extract', 'build'],
                        help="'extract' to run dpm install, 'build' to process data")

    args = parser.parse_args()

    if args.command == 'extract':
        extract_command()
    elif args.command == 'build':
        build_command()
    elif args.command == 'toml':
        build_toml()



if __name__ == '__main__':
    main()
