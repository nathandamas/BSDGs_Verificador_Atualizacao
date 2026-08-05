# Compilar o executável Windows x64 pelo GitHub Actions

1. Crie um repositório no GitHub ou use um repositório privado existente.
2. Envie **todo o conteúdo desta pasta** para a raiz do repositório, incluindo `.github/workflows/build-windows-x64.yml`.
3. Abra a guia **Actions** do repositório.
4. Selecione **Build Windows x64**.
5. Clique em **Run workflow**.
6. Aguarde a conclusão do job `build`.
7. Na seção **Artifacts**, baixe `BSDGs-Verificador-v1.3.0-Windows-x64`.
8. Extraia o ZIP. Ele conterá:
   - `BSDGs_Verificador_Atualizacao_v1.3.0_windows_x64.exe`;
   - o checksum SHA-256 correspondente.

O workflow usa `windows-2022`, Python 3.12 com `architecture: x64`, executa os testes, gera um único `.exe` e confirma no cabeçalho PE o código AMD64 `0x8664` antes de publicar o artefato.
