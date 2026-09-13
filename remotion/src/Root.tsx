import React from 'react';
import { Composition } from 'remotion';
import { HeroLoop } from './compositions/HeroLoop';
import { LacoBusca, LacoDiagrama, LacoRegistro } from './compositions/LacosDeSecao';
import { BoasVindas, ComoComecar, SeloAssinatura } from './compositions/BoasVindas';
import { DURACAO_FAIXA, FaixaVaiVem } from './compositions/FaixaVaiVem';
import { DURACAO_FAIXA_REGISTRO, FaixaRegistro } from './compositions/FaixaRegistro';
import { DURACAO_FAIXA_DIAGRAMA, FaixaDiagrama } from './compositions/FaixaDiagrama';
import { DURACAO_FAIXA_ROTEIROS, FaixaRoteiros } from './compositions/FaixaRoteiros';
import { DURACAO_FAIXA_PARA_QUEM, FaixaParaQuem } from './compositions/FaixaParaQuem';
import { DURACOES, FPS } from './theme';

/**
 * Quatro laços: um longo, no hero, e três curtos, um por seção da landing.
 * Cada um rende um MP4 e um pôster PNG/JPEG em landing/public/videos — o pôster
 * é o cartaz do <video> e o que aparece para quem pede movimento reduzido.
 */
export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="HeroLoop"
      component={HeroLoop}
      durationInFrames={DURACOES.hero}
      fps={FPS}
      width={1920}
      height={1080}
    />
    <Composition
      id="LacoBusca"
      component={LacoBusca}
      durationInFrames={DURACOES.busca}
      fps={FPS}
      width={1600}
      height={900}
    />
    <Composition
      id="LacoRegistro"
      component={LacoRegistro}
      durationInFrames={DURACOES.registro}
      fps={FPS}
      width={1600}
      height={1000}
    />
    {/* Faixa ultralarga da seção "Por que existe": na mão × no Revsist. */}
    <Composition
      id="FaixaVaiVem"
      component={FaixaVaiVem}
      durationInFrames={DURACAO_FAIXA}
      fps={FPS}
      width={2560}
      height={640}
    />
    {/* Faixa ultralarga da seção "Quando alguém perguntar": o registro. */}
    <Composition
      id="FaixaRegistro"
      component={FaixaRegistro}
      durationInFrames={DURACAO_FAIXA_REGISTRO}
      fps={FPS}
      width={2560}
      height={640}
    />
    {/* Faixa ultralarga da seção "No fim", no papel claro: o diagrama. */}
    <Composition
      id="FaixaDiagrama"
      component={FaixaDiagrama}
      durationInFrames={DURACAO_FAIXA_DIAGRAMA}
      fps={FPS}
      width={2560}
      height={640}
    />
    {/* Faixa da seção "Roteiros", no papel claro. */}
    <Composition
      id="FaixaRoteiros"
      component={FaixaRoteiros}
      durationInFrames={DURACAO_FAIXA_ROTEIROS}
      fps={FPS}
      width={2560}
      height={640}
    />
    {/* Faixa da seção "Para quem é", no azul-tinta. */}
    <Composition
      id="FaixaParaQuem"
      component={FaixaParaQuem}
      durationInFrames={DURACAO_FAIXA_PARA_QUEM}
      fps={FPS}
      width={2560}
      height={640}
    />
    <Composition
      id="LacoDiagrama"
      component={LacoDiagrama}
      durationInFrames={DURACOES.diagrama}
      fps={FPS}
      width={1920}
      height={1080}
    />

    {/* Peças do e-mail de aprovação de convite. Não são laços: o GIF roda uma
        vez e para, e os dois PNG são quadros únicos. */}
    <Composition
      id="BoasVindas"
      component={BoasVindas}
      durationInFrames={285}
      fps={FPS}
      width={1200}
      height={676}
    />
    <Composition
      id="ComoComecar"
      component={ComoComecar}
      durationInFrames={1}
      fps={FPS}
      width={1240}
      height={318}
    />
    <Composition
      id="SeloAssinatura"
      component={SeloAssinatura}
      durationInFrames={1}
      fps={FPS}
      width={900}
      height={200}
    />
  </>
);
