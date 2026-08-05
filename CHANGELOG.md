# Changelog

## 1.3.1 — seleção explícita da BSDG

- indicação permanente da **BSDG selecionada** na tela inicial;
- nova coluna visual de seleção com caixas `☐` e `☑` na tabela de BSDGs;
- persistência local da BSDG selecionada entre execuções do aplicativo;
- campo **BSDG selecionada** na tela de agendamento, abaixo das pastas de relatórios e logs;
- agendamento semanal vinculado efetivamente à BSDG selecionada;
- separação entre a BSDG atualmente selecionada e a BSDG já vinculada à tarefa do Windows;
- identificação da BSDG nas caixas de escolha de saída, no resumo da execução e na aba de resultados;
- exibição conjunta da BSDG, da pasta de relatórios e da pasta de logs nos contextos pertinentes;
- versão atualizada para 1.3.1.

## 1.3.0 — seleção de saída e data/hora local

- seleção obrigatória das pastas de relatórios e logs antes de cada verificação manual;
- configuração das pastas de saída para verificações agendadas;
- persistência das últimas pastas escolhidas no arquivo de configuração;
- validação de existência e permissão de gravação das pastas;
- uso das pastas configuradas pela execução silenciosa do Agendador de Tarefas;
- botões **Abrir relatórios** e **Abrir logs** passam a abrir as pastas configuradas;
- data e hora da última execução exibidas como `dd/mm/aaaa às hh:mm:ss (UTC±hh:mm)`;
- versão atualizada para 1.3.0.

## 1.2.0 — identidade visual LAGEAMB/GeoLitoral

- novo cabeçalho institucional com logotipo LAGEAMB e curvas de nível;
- paleta visual baseada no verde institucional;
- cartões de indicadores, abas, botões, tabelas, barra de progresso e rodapé padronizados;
- janela **Sobre** redesenhada, com site do LAGEAMB e GitHub do desenvolvedor;
- ícone próprio para o aplicativo e para o executável;
- detecção automática de `Montserrat Alternates`, com fallbacks seguros;
- recursos gráficos empacotados no EXE one-file pelo PyInstaller;
- nova função `resource_path()` para localizar recursos no código-fonte e no `_MEIPASS`;
- linhas de resultados e BSDGs com diferenciação visual por situação;
- documentação da identidade visual e captura de referência da interface;
- seis testes automatizados preservados e aprovados.

## 1.1.0

- correção de `BSDG_ComunidadesNoMapa` e `BSDG_Internacionalização`;
- aviso permanente de execução local;
- janela **Sobre** com versão, autoria e GitHub;
- melhorias na enumeração recursiva de GeoPackages e na mensagem de varredura sem arquivos.
