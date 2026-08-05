# BSDGs — Verificador de Atualização

Aplicação desktop para inventariar e validar periodicamente arquivos GeoPackage (`.gpkg`) armazenados em pastas de BSDGs sincronizadas do SharePoint pelo OneDrive.

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
- pode ser empacotada como `.exe` com PyInstaller.

A versão 1 **não importa dados para PostgreSQL/PostGIS**. Essa separação evita que arquivos incompletos, inválidos ou ainda em sincronização alterem automaticamente o banco de dados.

## 2. Arquitetura

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
│   ├── paths.py               # diretórios da aplicação
│   ├── reports.py             # relatórios CSV/JSON
│   ├── scanner.py             # descoberta e hash dos arquivos
│   ├── scheduler.py           # integração com schtasks.exe
│   └── service.py             # orquestração completa da varredura
├── tests/
├── install_dev.bat
├── run_dev.bat
├── build_exe.bat
└── BSDGs_Verificador_Atualizacao.spec
```

## 3. Ambiente recomendado

- Windows 11;
- Python 3.11 ou 3.12;
- Tkinter incluído no instalador oficial do Python;
- execução em ambiente virtual;
- PyInstaller apenas para gerar o executável.

A aplicação em tempo de execução usa somente a biblioteca padrão do Python. Portanto, não depende de GDAL, Fiona, GeoPandas ou QGIS para a prova de conceito.

## 4. Instalação para desenvolvimento

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

## 5. Executar a interface

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

## 6. Dados locais da aplicação

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

## 7. Validação executada

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

## 8. Arquivos somente na nuvem

O programa consulta atributos de arquivo do Windows. Quando detecta `FILE_ATTRIBUTE_OFFLINE` ou `FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS`, ele registra **SOMENTE NA NUVEM** e não abre o conteúdo, evitando download involuntário.

Para disponibilizar uma pasta:

1. clique com o botão direito sobre a pasta no Explorador;
2. escolha **Sempre manter neste dispositivo**;
3. aguarde o ícone verde do OneDrive;
4. execute novamente a verificação.

## 9. Agendamento semanal

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

## 10. Gerar o EXE

Execute:

```bat
build_exe.bat
```

Resultado:

```text
dist\BSDGs_Verificador_Atualizacao.exe
```

### Windows ARM64

A aplicação-fonte é compatível com Python nativo em ARM64 porque usa apenas biblioteca padrão. O executável gerado acompanha a arquitetura do interpretador e do bootloader do PyInstaller usados no processo de build.

Procedimento recomendado:

1. tente primeiro com Python ARM64 e PyInstaller atual;
2. registre a arquitetura mostrada pelo `build_exe.bat`;
3. execute testes no próprio Surface/PC ARM;
4. caso o bootloader ARM64 não esteja disponível no pacote instalado, use temporariamente Python x64 sob emulação do Windows ou compile o bootloader do PyInstaller com Visual Studio para ARM64.

Não distribua um executável sem testá-lo na arquitetura-alvo.

## 11. Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 12. Fluxo operacional recomendado

1. manter a BSDG_Litoral sincronizada;
2. marcar a raiz `geopackage` como **Sempre manter neste dispositivo**;
3. executar uma verificação manual inicial;
4. revisar os arquivos inválidos e somente na nuvem;
5. instalar o agendamento semanal;
6. cadastrar as demais BSDGs à medida que forem sincronizadas;
7. somente após estabilizar o inventário, desenvolver a etapa de carga controlada no `bdg_teste`.
