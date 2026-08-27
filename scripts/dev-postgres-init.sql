-- Banco separado para a suíte de testes, criado na primeira subida do volume.
-- Manter os testes fora do banco de desenvolvimento evita que uma execução
-- apague o projeto que se estava usando para conferir alguma coisa à mão.
CREATE DATABASE rsac_test OWNER rsac;
