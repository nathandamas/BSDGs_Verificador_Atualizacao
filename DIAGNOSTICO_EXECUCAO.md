# Diagnóstico de execução — versão 1.3.2

Esta versão diferencia três situações:

1. **o Windows impede o início do processo**: nenhum arquivo de diagnóstico é criado;
2. **o processo inicia, mas a interface falha**: é criado `startup_error.log`;
3. **a interface inicia corretamente**: o autoteste gera JSON com `"status": "OK"`.

## Teste manual

No PowerShell, dentro da pasta do executável:

```powershell
$exe = ".\BSDGs_Verificador_Atualizacao_v1.3.2_windows_x64.exe"
$diag = "$env:TEMP\bsdgs_self_test.json"
Unblock-File -LiteralPath $exe
$p = Start-Process -FilePath $exe -ArgumentList @("--self-test-file", $diag) -PassThru -Wait
$p.ExitCode
Get-Content $diag
```

Se a interface falhar na abertura normal, consulte:

```text
%LOCALAPPDATA%\BSDGs_Verificador_Atualizacao\startup_error.log
```

## Interpretação

- código `0` e `status: OK`: o executável e o Tkinter iniciaram; investigue bloqueio local, antivírus ou política corporativa na abertura normal;
- código diferente de `0` com JSON: o campo `traceback` indica o erro de inicialização;
- ausência de JSON e de `startup_error.log`: o Windows ou o antivírus bloqueou o executável antes da execução do Python.
