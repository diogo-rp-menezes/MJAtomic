"""
Script utilitário para corrigir erro do PGVectorStore relacionado à coluna de ID.

Problema observado:
  "Falha crítica ao inicializar PGVectorStore: Id column, <...>, does not exist."

Causa provável:
- Uma tabela existente com o mesmo nome de coleção foi criada anteriormente
  com um esquema legado/incompatível (coluna id diferente, sem a coluna
  padrão esperada pelo langchain-postgres atual).

Ação deste script:
- Descobrir o nome da tabela (coleção) pelo env `PGVECTOR_COLLECTION_NAME`
  (default: "code_collection").
- Conectar no Postgres usando a mesma lógica de normalização do projeto
  (usa `get_db_connection_string()` do módulo checkpoint, que devolve
  DSN plano `postgresql://` com porta 5433 se necessário).
- Exibir as colunas atuais (se a tabela existir) para diagnóstico.
- Executar `DROP TABLE IF EXISTS <tabela> CASCADE`.

Após isso, a aplicação poderá recriar a tabela com o esquema correto
na próxima inicialização/uso do `PGVectorStore.create_sync`.
"""

import os
import sys
from typing import List

import psycopg
from psycopg import sql

try:
    # Reutiliza nossa normalização de DSN (remove +driver e aplica porta 5433)
    from src.core.graph.checkpoint import get_db_connection_string
except Exception as e:
    print(f"[drop_pgvector_table] ERRO: não foi possível importar get_db_connection_string: {e}")
    sys.exit(2)


def list_columns(conn: psycopg.Connection, table_name: str) -> List[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table_name,),
        )
        rows = cur.fetchall()
        return [r[0] for r in rows]


def main():
    table_name = os.getenv("PGVECTOR_COLLECTION_NAME", "code_collection")
    dsn = get_db_connection_string()

    print(f"[drop_pgvector_table] DSN: {dsn}")
    print(f"[drop_pgvector_table] Tabela alvo (coleção): {table_name}")

    # O psycopg3 aceita DSN `postgresql://...` (sem +psycopg)
    try:
        with psycopg.connect(dsn) as conn:
            conn.autocommit = True

            # Diagnóstico: listar colunas se a tabela existir
            try:
                cols = list_columns(conn, table_name)
                if cols:
                    print(f"[drop_pgvector_table] Colunas atuais em '{table_name}': {cols}")
                else:
                    print(f"[drop_pgvector_table] Tabela '{table_name}' não encontrada (sem colunas).")
            except Exception as e:
                print(f"[drop_pgvector_table] Aviso ao listar colunas: {e}")

            # Drop da tabela (com CASCADE para remover dependências/índices)
            with conn.cursor() as cur:
                query = sql.SQL("DROP TABLE IF EXISTS {} CASCADE;").format(sql.Identifier(table_name))
                cur.execute(query)
                print(f"[drop_pgvector_table] DROP TABLE IF EXISTS {table_name} CASCADE executado com sucesso.")

    except Exception as e:
        print(f"[drop_pgvector_table] ERRO ao conectar/executar no Postgres: {e}")
        sys.exit(1)

    print("[drop_pgvector_table] Concluído. A aplicação deverá recriar a tabela com o esquema correto no próximo uso.")


if __name__ == "__main__":
    main()
