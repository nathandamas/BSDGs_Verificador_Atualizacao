# Identidade visual da interface — versão 1.3.0

A interface foi harmonizada com as aplicações do LAGEAMB/GeoLitoral fornecidas como referência.

## Elementos aplicados

- logotipo institucional no cabeçalho e na janela **Sobre**;
- curvas de nível como elemento gráfico de fundo;
- verde institucional principal `#7DB34E`;
- verde escuro de contraste `#4F7F2E`;
- superfícies brancas e fundo cinza-esverdeado claro;
- abas, cabeçalhos de tabela, botões primários e barra de progresso em verde;
- cartões de indicadores com borda superior verde;
- rodapé institucional;
- ícone próprio no executável e nas janelas;
- hierarquia tipográfica baseada em **Montserrat Alternates**.

## Fonte

A aplicação procura, nesta ordem:

1. `Montserrat Alternates`;
2. `Montserrat`;
3. `Segoe UI`;
4. fonte padrão do Tk.

O arquivo da fonte não é incorporado ao projeto nem ao executável. Para reprodução tipográfica exata, a fonte deve estar instalada no Windows do usuário. A ausência da fonte não impede o funcionamento da aplicação.

## Recursos empacotados

Os recursos gráficos ficam em `assets/` e são incluídos no EXE pelo arquivo `.spec` do PyInstaller. O acesso em modo de desenvolvimento e no executável one-file é resolvido por `resource_path()`.
