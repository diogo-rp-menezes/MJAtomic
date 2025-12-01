import sys
import os

# Adiciona a raiz do projeto (que contém 'src') ao sys.path
# Isso garante que os testes possam encontrar os módulos da aplicação
# como 'from src.core...'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')

if src_path not in sys.path:
    sys.path.insert(0, src_path)

if project_root not in sys.path:
    sys.path.insert(0, project_root)
