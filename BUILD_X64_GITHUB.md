# Compilar o executável Windows x64 pelo GitHub Actions

1. Envie os arquivos desta atualização para os mesmos caminhos do repositório.
2. Abra a guia **Actions** do repositório.
3. Selecione **Build Windows x64**.
4. Clique em **Run workflow**.
5. Aguarde a conclusão do job `build`.
6. Na seção **Artifacts**, baixe `BSDGs-Verificador-v1.3.1-Windows-x64`.
7. Extraia o ZIP. Ele conterá:
   - `BSDGs_Verificador_Atualizacao_v1.3.1_windows_x64.exe`;
   - o checksum SHA-256 correspondente.

O workflow usa `windows-2022`, Python 3.12 com `architecture: x64`, executa os testes, gera um único `.exe` e confirma no cabeçalho PE o código AMD64 `0x8664` antes de publicar o artefato.
