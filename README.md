# BSDGs — Verificador de Atualização

Aplicação desktop para inventariar e validar periodicamente arquivos GeoPackage (`.gpkg`) armazenados em pastas de BSDGs sincronizadas do SharePoint pelo OneDrive.

> **Modo de operação local:** o executável não acessa o SharePoint diretamente. Ele verifica exclusivamente as pastas que o OneDrive disponibiliza no computador em que a aplicação está sendo executada. Para validar o conteúdo dos GeoPackages, os arquivos precisam estar disponíveis localmente.

## 1. Escopo da versão 1

A aplicação:

- cadastra várias BSDGs e uma pasta local para cada uma;
- percorre subpastas e localiza arquivos `.gpkg`;
- detecta arquivos novos, modificados, sem alteração e removidos;
- identifica arquivos do OneDrive que ainda estão somente na nuvem;
- valida a estrutura SQLite/GeoPackage;
- consulta `gpkg_contents`, `gpkg_geometry_columns` e `gpkg_spatial_ref_sys`;
- registra tipo de geometria e SRID declarados por camada;
- mantém inventário histórico em SQLite;
- gera relatórios CSV e JSON;
- cria logs técnicos;
- instala uma execução semanal no Agendador de Tarefas do Windows;
- pode ser empacotada como um único `.exe` com PyInstaller;
- apresenta aviso permanente de execução local e janela **Sobre** com versão, autoria e GitHub do desenvolvedor.

A versão 1 **não importa dados para PostgreSQL/PostGIS**. Essa separação evita que arquivos incompletos, inválidos ou ainda em sincronização alterem automaticamente o banco de dados.

O catálogo inicial inclui, entre outras, as entradas corrigidas:

- `BSDG_ComunidadesNoMapa`;
- `BSDG_Internacionalização`.

Configurações antigas com os nomes truncados são migradas automaticamente ao abrir a versão 1.3.0.


## 2. Identidade visual LAGEAMB

A versão 1.3.0 incorpora a identidade visual das aplicações do LAGEAMB/GeoLitoral:

- logotipo institucional no cabeçalho e na janela **Sobre**;
- curvas de nível como elemento gráfico de fundo;
- paleta institucional com verde principal `#7DB34E`;
- abas, botões, cabeçalhos de tabela, indicadores e barra de progresso padronizados;
- cartões de resumo e rodapé institucional;
- ícone próprio no executável;
- fonte preferencial **Montserrat Alternates**.

A fonte é detectada no Windows. Quando `Montserrat Alternates` não está instalada, a aplicação utiliza `Montserrat`, `Segoe UI` ou a fonte padrão do Tk, sem impedir a execução. O arquivo da fonte não é incorporado ao EXE.

Os arquivos gráficos ficam na pasta `assets/` e são incluídos automaticamente no executável pelo arquivo `.spec`. Consulte também `GUI_IDENTIDADE_VISUAL.md`.

## 3. Pastas de saída por execução

Antes de cada verificação manual, o aplicativo solicita a pasta dos relatórios e a pasta dos logs. As escolhas são validadas, armazenadas como padrão e podem ser alteradas novamente na execução seguinte.

No agendamento semanal, as duas pastas são definidas na aba **Agendamento** e usadas pela execução silenciosa do Windows.

A data e a hora da última execução são exibidas no formato brasileiro (`dd/mm/aaaa`, `hh:mm:ss`) com o deslocamento UTC registrado.


## 4. Arquitetura

```text
BSDGs_Verificador_Atualizacao/
├── main.py
├── bsdgs_verifier/
│   ├── cli.py                 # modo silencioso e comandos administrativos
│   ├── config.py              # catálogo das BSDGs e preferências
│   ├── constants.py           # constantes e enumerações gerais
│   ├── gpkg_validator.py      # validação estrutural dos GeoPackages
│   ├── gui.py                 # interface Tkinter/ttk
│   ├── inventory.py           # inventário SQLite
│   ├── logging_setup.py       # logs
│   ├── models.py              # modelos de dados
│   ├── onedrive.py            # estado local/somente na nuvem
│   ├── paths.py               # diretórios e resolução de recursos
│   ├── theme.py               # paleta, tipografia e estilos ttk
│   ├── reports.py             # relatórios CSV/JSON
│   ├── scanner.py             # descoberta e hash dos arquivos
│   ├── scheduler.py           # integração com schtasks.exe
│   └── service.py             # orquestração completa da varredura
├── assets/                    # logotipos, curvas de nível e ícone
├── tests/
├── GUI_IDENTIDADE_VISUAL.md
├── install_dev.bat
├── run_dev.bat
├── build_exe.bat
├── build_exe_unico.bat       # gera a pasta release com somente o EXE distribuível
└── BSDGs_Verificador_Atualizacao.spec
```

## 5. Ambiente recomendado

- Windows 11;
- Python 3.11 ou 3.12;
- Tkinter incluído no instalador oficial do Python;
- execução em ambiente virtual;
- PyInstaller apenas para gerar o executável.

A aplicação em tempo de execução usa somente a biblioteca padrão do Python. Portanto, não depende de GDAL, Fiona, GeoPandas ou QGIS para a prova de conceito.

## 6. Instalação para desenvolvimento

No Explorador de Arquivos, abra a pasta do projeto e execute:

```bat
install_dev.bat
```

Ou pelo terminal:

```powershell
cd C:\caminho\BSDGs_Verificador_Atualizacao
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## 7. Executar a interface

```bat
run_dev.bat
```

Ou:

```powershell
.\.venv\Scripts\python.exe main.py
```

Na primeira execução, a configuração é criada automaticamente. A BSDG_Litoral recebe o caminho:

```text
C:\Users\<usuario>\ufpr.br\Banco de Dados Geográficos do LAGEAMB - BDG_Litoral\dadosGeoespaciais\geopackage
```

O caminho é montado a partir da pasta pessoal do usuário. Ele pode ser alterado na aba **BSDGs monitoradas**.

## 8. Dados locais da aplicação

No Windows:

```text
%LOCALAPPDATA%\BSDGs_Verificador_Atualizacao\
```

Estrutura:

```text
config\bsdgs.json
database\inventario_bsdgs.sqlite
reports\*.csv e *.json
logs\*.log
```

Para usar uma pasta de testes diferente, defina:

```powershell
$env:BSDGS_VERIFIER_HOME = "C:\temp\BSDGs_Verificador"
python main.py
```

## 9. Validação executada

O validador confirma:

1. arquivo não vazio;
2. cabeçalho SQLite válido;
3. existência de `gpkg_spatial_ref_sys` e `gpkg_contents`;
4. `PRAGMA quick_check`;
5. existência das tabelas declaradas em `gpkg_contents`;
6. registro em `gpkg_geometry_columns` para cada camada vetorial;
7. existência da coluna geométrica declarada;
8. tipo de geometria conhecido;
9. existência do `srs_id` em `gpkg_spatial_ref_sys`;
10. consistência básica de Z e M.

### Limitação importante

Sem GDAL/OGR, a versão 1 valida a **declaração estrutural** do tipo geométrico e do SRID. Ela não percorre todos os blobs geométricos para provar que cada feição concreta corresponde ao tipo declarado. Uma auditoria geométrica profunda pode ser adicionada na versão 2 com `ogrinfo`, GDAL ou QGIS Processing.

## 10. Arquivos somente na nuvem

O programa consulta atributos de arquivo do Windows. Quando detecta `FILE_ATTRIBUTE_OFFLINE` ou `FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS`, ele registra **SOMENTE NA NUVEM** e não abre o conteúdo, evitando download involuntário.

Para disponibilizar uma pasta:

1. clique com o botão direito sobre a pasta raiz monitorada no Explorador;
2. escolha **Sempre manter neste dispositivo**;
3. aguarde a conclusão da sincronização e o indicador verde;
4. confirme na aba **BSDGs monitoradas** que **Subpastas = Sim**;
5. execute novamente a verificação.

Quando uma pasta existe, mas nenhum `.gpkg` é enumerado, a versão 1.3.0 registra o estado **ATENÇÃO: NENHUM GPKG LOCALIZADO** e apresenta orientações em linguagem não técnica.

## 11. Agendamento semanal

A interface chama `schtasks.exe` e cria a tarefa:

```text
BSDGs - Verificador de Atualizacao
```

A tarefa executa:

```text
BSDGs_Verificador_Atualizacao.exe --scan-all-silent
```

ou, no modo de desenvolvimento:

```text
python.exe main.py --scan-all-silent
```

A tarefa usa execução interativa e privilégio limitado. Isso é deliberado: o usuário precisa estar conectado para que o cliente OneDrive e as pastas sincronizadas estejam disponíveis.

Comandos equivalentes:

```powershell
python main.py --install-schedule --day FRI --time 18:00
python main.py --remove-schedule
```

## 12. Gerar um único arquivo EXE

A especificação fornecida já usa o modo **one-file**. Para gerar uma pasta de distribuição contendo somente o executável, execute:

```bat
build_exe_unico.bat
```

Resultado final para distribuição:

```text
release\BSDGs_Verificador_Atualizacao.exe
```

Envie somente esse arquivo. O destinatário não precisa instalar Python, copiar o código-fonte nem receber o ambiente `.venv`. Na primeira execução, o aplicativo cria automaticamente sua configuração, inventário, relatórios e logs em `%LOCALAPPDATA%\BSDGs_Verificador_Atualizacao`.

A pessoa que receber o executável ainda precisa:

1. usar Windows;
2. ter as bibliotecas do SharePoint sincronizadas pelo OneDrive;
3. selecionar as pastas locais na aba **BSDGs monitoradas**;
4. manter os GeoPackages disponíveis no dispositivo;
5. instalar o agendamento novamente naquele computador, caso deseje a execução semanal.

### Windows ARM64

A aplicação-fonte é compatível com Python nativo em ARM64 porque usa apenas biblioteca padrão. O executável gerado acompanha a arquitetura do interpretador e do bootloader do PyInstaller usados no processo de build.

Procedimento recomendado:

1. tente primeiro com Python ARM64 e PyInstaller atual;
2. registre a arquitetura mostrada pelo `build_exe.bat`;
3. execute testes no próprio Surface/PC ARM;
4. caso o bootloader ARM64 não esteja disponível no pacote instalado, use temporariamente Python x64 sob emulação do Windows ou compile o bootloader do PyInstaller com Visual Studio para ARM64.

Não distribua um executável sem testá-lo na arquitetura-alvo.

## 13. Como confirmar que o executável está funcionando

Faça este teste controlado:

1. abra a aplicação e confirme no título **v1.3.0**;
2. abra **Ajuda > Sobre** e confirme autoria, versão e link do GitHub;
3. na aba **BSDGs monitoradas**, confirme que a pasta existe, está ativada e **Subpastas = Sim**;
4. coloque um GeoPackage pequeno e conhecido em uma subpasta local;
5. execute **Verificar todas agora**;
6. confirme que o resumo apresenta `Arquivos: 1` ou mais;
7. abra **Resultados e logs** e confira o arquivo, o tipo geométrico, o SRID e a situação de validação;
8. abra o relatório JSON e confirme que `total_files` e `discovered_files` são maiores que zero;
9. execute uma segunda vez sem alterar o arquivo e confirme o estado **SEM ALTERAÇÃO**.

Interpretação dos resultados:

- **CONCLUÍDA + arquivos > 0:** varredura e inventário funcionando;
- **CONCLUÍDA + arquivos = 0:** o programa foi executado, mas não encontrou GeoPackages; verifique sincronização, disponibilidade local, extensão e pesquisa em subpastas;
- **SOMENTE NA NUVEM:** o arquivo foi enumerado, mas não foi aberto para evitar download involuntário;
- **VÁLIDO:** a estrutura GeoPackage e os metadados mínimos foram validados;
- **INVÁLIDO/ERRO DE LEITURA:** consulte o relatório e o log.

## 14. Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 15. Fluxo operacional recomendado

1. manter a BSDG_Litoral sincronizada;
2. marcar a raiz `geopackage` como **Sempre manter neste dispositivo**;
3. executar uma verificação manual inicial;
4. revisar os arquivos inválidos e somente na nuvem;
5. instalar o agendamento semanal;
6. cadastrar as demais BSDGs à medida que forem sincronizadas;
7. somente após estabilizar o inventário, desenvolver a etapa de carga controlada no `bdg_teste`.

## 16. Informações da aplicação

- Nome: **BSDGs — Verificador de Atualização**
- Versão: **1.3.0**
- Desenvolvimento: **Nathan Damas**
- GitHub: `https://github.com/nathandamas`

Essas informações também aparecem na janela **Ajuda > Sobre**.
