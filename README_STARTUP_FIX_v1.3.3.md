# Correção de inicialização — versão 1.3.3

## Diagnóstico confirmado

Mesmo com uma única instância e estado local novo, o processo permaneceu ativo
sem criar uma janela principal (`MainWindowHandle = 0`).

A versão 1.3.3 altera o fluxo de inicialização:

1. cria a raiz Tk;
2. constrói a estrutura visual;
3. apresenta e centraliza a janela;
4. entra no ciclo de eventos;
5. inicializa `InventoryDB` e `VerificationService` em segundo plano;
6. atualiza o painel somente depois que o inventário estiver disponível.

Também foi adicionado:

- bloqueio de instância única por mutex do Windows;
- `startup_trace.log` com cada etapa;
- autoteste completo da inicialização adiada;
- versão e artefatos atualizados para 1.3.3.

## Arquivos novos

- `bsdgs_verifier/deferred_gui.py`
- `bsdgs_verifier/instance_lock.py`

## Arquivos a substituir

- `main.py`
- `bsdgs_verifier/cli.py`
- `bsdgs_verifier/constants.py`
- `BSDGs_Verificador_Atualizacao.spec`
- `.github/workflows/build-windows-x64.yml`

## Depois do build

Baixe o artefato:

`BSDGs-Verificador-v1.3.3-Windows-x64`

Antes de testar, encerre todas as instâncias antigas da v1.3.2. Não é necessário
apagar novamente a pasta de dados.

Se houver nova falha, consulte:

`%LOCALAPPDATA%\BSDGs_Verificador_Atualizacao\startup_trace.log`
