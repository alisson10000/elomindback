-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 24/03/2026 às 19:09
-- Versão do servidor: 10.4.32-MariaDB
-- Versão do PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `elomind`
--

-- --------------------------------------------------------

--
-- Estrutura para tabela `anamnesis`
--

CREATE TABLE `anamnesis` (
  `id` int(11) NOT NULL,
  `client_id` int(11) NOT NULL,
  `therapist_id` int(11) NOT NULL,
  `summary` text NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `consents`
--

CREATE TABLE `consents` (
  `id` int(11) NOT NULL,
  `client_id` int(11) NOT NULL,
  `accepted_at` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `consents`
--

INSERT INTO `consents` (`id`, `client_id`, `accepted_at`) VALUES
(4, 7, '2026-02-15 18:07:31'),
(5, 8, '2026-02-20 14:36:56'),
(6, 9, '2026-03-07 14:02:13');

-- --------------------------------------------------------

--
-- Estrutura para tabela `data_deletion_requests`
--

CREATE TABLE `data_deletion_requests` (
  `id` int(11) NOT NULL,
  `client_id` int(11) NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'pending',
  `requested_at` datetime NOT NULL DEFAULT current_timestamp(),
  `completed_at` datetime DEFAULT NULL,
  `client_email` varchar(255) DEFAULT NULL,
  `client_name` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `dreams`
--

CREATE TABLE `dreams` (
  `id` int(11) NOT NULL,
  `client_id` int(11) NOT NULL,
  `therapist_id` int(11) NOT NULL,
  `description` text NOT NULL,
  `therapist_tags` text DEFAULT NULL,
  `therapist_notes` text DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `dreams`
--

INSERT INTO `dreams` (`id`, `client_id`, `therapist_id`, `description`, `therapist_tags`, `therapist_notes`, `created_at`, `updated_at`) VALUES
(5, 7, 2, 'Sonhei com a luz no fim do tunel', 'esperana', 'A paciente esta tendo novas perspectivas', '2026-02-16 12:28:10', '2026-02-20 14:25:53'),
(6, 7, 2, 'Sonhei que no final do tunel nao tinha luz estava escuro', NULL, NULL, '2026-03-03 12:58:17', '2026-03-03 12:58:17'),
(7, 7, 2, 'Sonhei que no final do tunel tinha uma luz', NULL, NULL, '2026-03-07 13:52:36', '2026-03-07 13:52:36');

-- --------------------------------------------------------

--
-- Estrutura para tabela `feedback`
--

CREATE TABLE `feedback` (
  `id` int(11) NOT NULL,
  `reflection_id` int(11) NOT NULL,
  `ia_generated_content` text NOT NULL,
  `ia_neuro_nutrition_tip` varchar(500) DEFAULT NULL,
  `ia_activity_suggestion` varchar(500) DEFAULT NULL,
  `status` enum('pending_approval','approved','rejected') NOT NULL,
  `therapist_approved_by` int(11) DEFAULT NULL,
  `therapist_notes` text DEFAULT NULL,
  `approved_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `feedback`
--

INSERT INTO `feedback` (`id`, `reflection_id`, `ia_generated_content`, `ia_neuro_nutrition_tip`, `ia_activity_suggestion`, `status`, `therapist_approved_by`, `therapist_notes`, `approved_at`, `created_at`) VALUES
(12, 20, 'É maravilhoso saber que você se sente mais aliviado após as sessões de terapia e reconhece o poder do perdão em trazer leveza. No entanto, é compreensível sentir resistência ao se abrir com os outros, pois isso pode ser um processo desafiador. Cada passo em direção à abertura é um sinal de crescimento e autoconhecimento. Como você poderia facilitar essa sua disposição para compartilhar com quem confia?sdfgsdgfsd', 'Incluir alimentos ricos em fibras, como frutas e vegetais, pode beneficiar a saúde do seu intestino e, consequentemente, a função cerebral.', 'Que tal fazer uma caminhada curta ao ar livre para refletir sobre suas experiências e conectar-se com o ambiente?', 'approved', 2, 'Observei uma leve melhora no paciente', '2026-02-16 15:25:40', '2026-02-16 15:24:05'),
(13, 21, 'É natural sentir apreensão ao considerar mudanças, especialmente quando sabemos que elas não são fáceis. Você já percebeu que, mesmo com esse sentimento, conseguiu encontrar forças para realizar suas atividades diárias, o que é um grande passo! Essa resistência à mudança é comum e pode ser desafiadora, mas lembre-se de que cada pequena ação conta. Que tal pensar em qual atitude específica você gostaria de mudar e como pode dar o primeiro passo nessa direção?', 'Incluir alimentos ricos em fibras na sua dieta pode favorecer a saúde do intestino, impactando positivamente seu bem-estar mental.', 'Faça uma caminhada leve de 10 a 15 minutos, em um ritmo confortável, apenas para movimentar o corpo.', 'approved', 2, NULL, '2026-02-20 17:31:54', '2026-02-20 17:31:40'),
(14, 22, 'É ótimo perceber que você se sentiu com menos tensão após a sessão, o que pode ser um sinal de que está começando a lidar melhor com suas preocupações. Reconhecer que muitas vezes nos preocupamos com problemas que não existem é um passo importante para encontrar mais leveza no dia a dia. Além disso, enfrentar a resistência em mudar hábitos pode ser desafiador, mas lembre-se de que pequenas mudanças podem levar a grandes transformações. Como você pode tornar essa mudança mais acessível e menos assustadora?', 'Incluir alimentos ricos em fibras, como frutas e vegetais, pode ajudar a manter sua microbiota intestinal saudável, impactando positivamente seu bem-estar mental.', 'Faça uma caminhada leve de 10 a 15 minutos, em um ritmo confortável, apenas para movimentar o corpo.', 'approved', 2, NULL, '2026-02-20 17:42:54', '2026-02-20 17:41:36'),
(15, 23, 'É compreensível que a ansiedade tenha aumentado após a sessão, especialmente quando a clareza não veio como esperado e você sentiu dificuldade em se abrir. Esses momentos são desafiadores e podem trazer uma sensação de frustração. Embora não tenha identificado um ponto positivo, cada experiência pode ensinar algo novo sobre si mesmo e sobre suas necessidades. O que poderia facilitar sua comunicação nas próximas sessões?', 'Incluir mais fibras na sua alimentação pode ajudar a equilibrar sua microbiota intestinal e, consequentemente, melhorar sua saúde mental.', 'Experimente fazer uma breve pausa para caminhar ao ar livre e sentir o sol, isso pode ajudar a clarear seus pensamentos.', 'approved', 2, 'O paciente teve uma recaida', '2026-03-03 16:02:51', '2026-03-03 16:01:40'),
(16, 24, 'É natural sentir agustiação ao revisitar lembranças antigas, especialmente quando esse processo traz à tona emoções desafiadoras. Abrir-se durante a terapia é um passo significativo, e é ótimo saber que você se sentiu mais leve após compartilhar seus sentimentos. Essa abertura pode ser um caminho poderoso para o autoconhecimento e a cura. Como você se sente agora em relação a essa experiência de se abrir?', 'Incluir alimentos ricos em fibras, como frutas e vegetais, pode beneficiar sua saúde intestinal e, consequentemente, seu bem-estar mental.', 'Tire alguns minutos para uma caminhada ao ar livre e aproveite a luz do sol.', 'approved', 2, 'Paciente teve uma piora no quadro mas conseguir se abrir', '2026-03-07 16:55:35', '2026-03-07 16:54:41'),
(17, 25, 'É natural sentir tristeza ao revisitar memórias do passado, como você mencionou. No entanto, é importante reconhecer que essa reflexão pode ser um passo importante para o seu crescimento pessoal, permitindo que você compartilhe suas experiências sem precisar carregar tudo sozinho. O ponto positivo de perceber que não precisa enfrentar tudo sozinho é valioso e abre espaço para o apoio de outras pessoas. Como você se sente ao pensar em compartilhar essas experiências com alguém de confiança?', 'Incluir alimentos ricos em fibras na sua dieta pode ajudar a manter uma microbiota saudável, o que é benéfico para o bem-estar mental.', 'Faça uma caminhada leve de 10 a 15 minutos, em um ritmo confortável, apenas para movimentar o corpo.', 'approved', 2, NULL, '2026-03-07 17:05:29', '2026-03-07 17:05:15');

-- --------------------------------------------------------

--
-- Estrutura para tabela `invitations`
--

CREATE TABLE `invitations` (
  `id` int(11) NOT NULL,
  `therapist_id` int(11) NOT NULL,
  `email` varchar(255) NOT NULL,
  `token_hash` varchar(255) NOT NULL,
  `expires_at` datetime NOT NULL,
  `used_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `invitations`
--

INSERT INTO `invitations` (`id`, `therapist_id`, `email`, `token_hash`, `expires_at`, `used_at`, `created_at`) VALUES
(6, 2, 'alisson.lima.souza@gmail.com', '1df126303a02eb7b12bb207ec165b15a048032a8f21333af7c5c18d087331a66', '2026-02-18 19:27:55', '2026-02-15 19:28:43', '2026-02-15 16:27:55'),
(7, 2, 'alisson.lima.souza@gmail.com', '0463329a8c82b2cfedd5f2f4782eeeae572b94e02c6ba5fa726b5a5d9a28d75e', '2026-02-18 21:06:08', '2026-02-15 21:07:04', '2026-02-15 18:06:08'),
(8, 2, 'emanuelesantosdesouza0@gmail.com', '2b2ae8cf01e47581fd4343794a505c1f42aa361fb9dbe6a6169ff4e81c6e6333', '2026-02-23 17:34:09', '2026-02-20 17:36:17', '2026-02-20 14:34:09'),
(9, 2, 'amandamelorh2026@gmail.com', 'ebe7b17828b77a623283948c63243612c95988ad5397bd3027431307dc903aba', '2026-03-10 16:59:46', '2026-03-07 17:01:37', '2026-03-07 13:59:46');

-- --------------------------------------------------------

--
-- Estrutura para tabela `password_reset_tokens`
--

CREATE TABLE `password_reset_tokens` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `token_hash` varchar(255) NOT NULL,
  `expires_at` datetime NOT NULL,
  `used` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `used_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `reflections`
--

CREATE TABLE `reflections` (
  `id` int(11) NOT NULL,
  `client_id` int(11) NOT NULL,
  `therapist_id` int(11) DEFAULT NULL,
  `feeling_after_session` text NOT NULL,
  `what_learned` text NOT NULL,
  `positive_point` text NOT NULL,
  `resistance_or_disagreement` text DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `reflections`
--

INSERT INTO `reflections` (`id`, `client_id`, `therapist_id`, `feeling_after_session`, `what_learned`, `positive_point`, `resistance_or_disagreement`, `created_at`, `updated_at`) VALUES
(20, 7, 2, 'Depois da terapia me senta mais aliviado', 'Que perdoar de deixa mais leve', 'Se abrir com as pessoas e um bom caminho', 'Para me abrir senti dificuldade', '2026-02-16 12:22:34', '2026-03-19 12:23:01'),
(21, 7, 2, 'Dessa vez me senti apreensivo', 'Que realizar mudancas nao e facil, mas e o melhor caminho', 'Apesar de apreensivo tive forcas para fazer minhas atividade do dia a dia', 'Apenas que mudar de attitude no e facil', '2026-02-20 14:30:01', '2026-03-19 12:23:01'),
(22, 8, 2, 'Com menos tensao', 'Que eu me preocupo muito', 'A importancia de nao me preocupar com problemas inexistentes', 'Na minhas propria dificuldade de mudar habitos', '2026-02-20 14:39:37', '2026-03-19 12:23:01'),
(23, 7, 2, 'Dessa vez nao me senti bem a minha ansiedade aumentou', 'Dessa vez no fiquei com a visao muito clara', 'Dessa vez nao teve ponto positivo', 'Nao consegui me abrir diretamente na sesao', '2026-03-03 12:57:03', '2026-03-19 12:23:01'),
(24, 7, 2, 'Hoje eu fiquei muito agustiado pois mexi em coisas antigas', 'Que o melhor caminho na terapia e se abrir', 'Me senti mais leve depois que me abri', 'Foi dificil falar', '2026-03-07 13:52:10', '2026-03-19 12:23:01'),
(25, 9, 2, 'Me senti triste pois tivi que falar coisas do passado', 'Apesar de sentir triste falar foi melhor', 'Que no tenho que carregar o mundo nas costas', 'Que falar e muito dificil', '2026-03-07 14:03:27', '2026-03-19 12:23:01'),
(26, 7, 2, 'sdfgs', 'fgsdfg', 'sdfgsdfg', 'sdfg', '2026-03-20 14:07:05', '2026-03-20 14:07:05'),
(27, 7, 2, 'Yfufu', 'Cucfugu', 'Vucuvuuv', 'J jvjvj', '2026-03-20 15:04:53', '2026-03-20 15:04:53'),
(28, 7, 2, 'Hcjfig', 'Jgjggj', 'Jvjvjg', 'J N nvjv', '2026-03-20 15:13:12', '2026-03-20 15:13:12'),
(29, 7, 2, 'Ugiggi', 'Hcucu', 'Uguvu', 'Ucucu', '2026-03-20 15:25:37', '2026-03-20 15:25:37'),
(30, 7, 2, 'Vufugug', 'Hihi github', 'Vjvuvivi', 'Vjcuvuv', '2026-03-20 15:47:15', '2026-03-20 15:47:15'),
(31, 7, 2, 'sdfgsdfg', 'sdfgsdfg', 'sdfgsdfg', 'sdfgsdfg', '2026-03-20 15:51:48', '2026-03-20 15:51:48'),
(32, 7, 2, '46545645', 'kpokpokp', 'ytyiuytuy', 'tyutyutuy', '2026-03-20 15:57:06', '2026-03-20 15:57:06');

-- --------------------------------------------------------

--
-- Estrutura para tabela `therapist_clients`
--

CREATE TABLE `therapist_clients` (
  `id` int(11) NOT NULL,
  `therapist_id` int(11) NOT NULL,
  `client_id` int(11) NOT NULL,
  `joined_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `therapist_clients`
--

INSERT INTO `therapist_clients` (`id`, `therapist_id`, `client_id`, `joined_at`) VALUES
(4, 2, 7, '2026-02-15 18:07:04'),
(5, 2, 8, '2026-02-20 14:36:17'),
(6, 2, 9, '2026-03-07 14:01:37');

-- --------------------------------------------------------

--
-- Estrutura para tabela `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `role` enum('client','therapist') NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `users`
--

INSERT INTO `users` (`id`, `email`, `password_hash`, `name`, `role`, `is_active`) VALUES
(2, 'terapeuta@email.com', '$2b$12$V6i2ohHftUniSp/WVihNs.kPaKJpZSvZX8zPk4OnO3A9swHaJLIye', 'Helena', 'therapist', 1),
(7, 'alisson.lima.souza@gmail.com', '$2b$12$vYYnT7f3B6cdxbhp8y6KhOhW82vWf1z.05n0/KRxphrESulq4gAI6', 'alisson', 'client', 1),
(8, 'emanuelesantosdesouza0@gmail.com', '$2b$12$.Gzmt9EyScIwBnyEmdNEw.97GpgtF5BFM2oC80lrKvG8RGlmvlra.', 'emanuele', 'client', 1),
(9, 'amandamelorh2026@gmail.com', '$2b$12$tE7QrRDJUx2ObCrq5DyBLelmkVFRFtincN0hIKh4hoWsXB6B6oAkC', 'Amanda', 'client', 1);

-- --------------------------------------------------------

--
-- Estrutura para tabela `user_push_tokens`
--

CREATE TABLE `user_push_tokens` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `expo_push_token` varchar(255) NOT NULL,
  `platform` varchar(20) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `user_push_tokens`
--

INSERT INTO `user_push_tokens` (`id`, `user_id`, `expo_push_token`, `platform`, `is_active`, `created_at`, `updated_at`) VALUES
(1, 7, 'ExponentPushToken[faCMYSCNxn3ZnqmPv71vTu]', 'android', 1, '2026-03-20 13:29:34', '2026-03-20 13:29:34'),
(2, 2, 'ExponentPushToken[0v7PteBgbrPB12rBNp7xYZ]', 'android', 1, '2026-03-20 14:54:05', '2026-03-20 15:56:29');

--
-- Índices para tabelas despejadas
--

--
-- Índices de tabela `anamnesis`
--
ALTER TABLE `anamnesis`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_anamnesis_client_therapist` (`client_id`,`therapist_id`),
  ADD KEY `ix_anamnesis_therapist_id` (`therapist_id`),
  ADD KEY `ix_anamnesis_client_id` (`client_id`),
  ADD KEY `ix_anamnesis_id` (`id`);

--
-- Índices de tabela `consents`
--
ALTER TABLE `consents`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `client_id` (`client_id`),
  ADD KEY `ix_consents_id` (`id`);

--
-- Índices de tabela `data_deletion_requests`
--
ALTER TABLE `data_deletion_requests`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ix_data_deletion_requests_client_id` (`client_id`),
  ADD KEY `ix_data_deletion_requests_status` (`status`),
  ADD KEY `ix_data_deletion_requests_id` (`id`);

--
-- Índices de tabela `dreams`
--
ALTER TABLE `dreams`
  ADD PRIMARY KEY (`id`),
  ADD KEY `ix_dreams_client_id` (`client_id`),
  ADD KEY `ix_dreams_therapist_id` (`therapist_id`),
  ADD KEY `ix_dreams_id` (`id`);

--
-- Índices de tabela `feedback`
--
ALTER TABLE `feedback`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ix_feedback_reflection_id` (`reflection_id`),
  ADD KEY `therapist_approved_by` (`therapist_approved_by`),
  ADD KEY `ix_feedback_status` (`status`),
  ADD KEY `ix_feedback_id` (`id`);

--
-- Índices de tabela `invitations`
--
ALTER TABLE `invitations`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ix_invitations_token_hash` (`token_hash`),
  ADD KEY `therapist_id` (`therapist_id`),
  ADD KEY `ix_invitations_email` (`email`),
  ADD KEY `ix_invitations_id` (`id`);

--
-- Índices de tabela `password_reset_tokens`
--
ALTER TABLE `password_reset_tokens`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ix_password_reset_tokens_token_hash` (`token_hash`),
  ADD KEY `ix_password_reset_tokens_user_id` (`user_id`),
  ADD KEY `ix_password_reset_tokens_id` (`id`);

--
-- Índices de tabela `reflections`
--
ALTER TABLE `reflections`
  ADD PRIMARY KEY (`id`),
  ADD KEY `client_id` (`client_id`),
  ADD KEY `ix_reflections_id` (`id`),
  ADD KEY `ix_reflections_therapist_id` (`therapist_id`);

--
-- Índices de tabela `therapist_clients`
--
ALTER TABLE `therapist_clients`
  ADD PRIMARY KEY (`id`),
  ADD KEY `therapist_id` (`therapist_id`),
  ADD KEY `client_id` (`client_id`);

--
-- Índices de tabela `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ix_users_email` (`email`),
  ADD KEY `ix_users_id` (`id`);

--
-- Índices de tabela `user_push_tokens`
--
ALTER TABLE `user_push_tokens`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_user_push_token` (`expo_push_token`),
  ADD KEY `ix_user_push_tokens_user_id` (`user_id`);

--
-- AUTO_INCREMENT para tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `anamnesis`
--
ALTER TABLE `anamnesis`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de tabela `consents`
--
ALTER TABLE `consents`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT de tabela `data_deletion_requests`
--
ALTER TABLE `data_deletion_requests`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de tabela `dreams`
--
ALTER TABLE `dreams`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT de tabela `feedback`
--
ALTER TABLE `feedback`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=18;

--
-- AUTO_INCREMENT de tabela `invitations`
--
ALTER TABLE `invitations`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT de tabela `password_reset_tokens`
--
ALTER TABLE `password_reset_tokens`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `reflections`
--
ALTER TABLE `reflections`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=33;

--
-- AUTO_INCREMENT de tabela `therapist_clients`
--
ALTER TABLE `therapist_clients`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT de tabela `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT de tabela `user_push_tokens`
--
ALTER TABLE `user_push_tokens`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- Restrições para tabelas despejadas
--

--
-- Restrições para tabelas `anamnesis`
--
ALTER TABLE `anamnesis`
  ADD CONSTRAINT `anamnesis_ibfk_1` FOREIGN KEY (`client_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `anamnesis_ibfk_2` FOREIGN KEY (`therapist_id`) REFERENCES `users` (`id`);

--
-- Restrições para tabelas `consents`
--
ALTER TABLE `consents`
  ADD CONSTRAINT `consents_ibfk_1` FOREIGN KEY (`client_id`) REFERENCES `users` (`id`);

--
-- Restrições para tabelas `data_deletion_requests`
--
ALTER TABLE `data_deletion_requests`
  ADD CONSTRAINT `data_deletion_requests_ibfk_1` FOREIGN KEY (`client_id`) REFERENCES `users` (`id`);

--
-- Restrições para tabelas `dreams`
--
ALTER TABLE `dreams`
  ADD CONSTRAINT `dreams_ibfk_1` FOREIGN KEY (`client_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `dreams_ibfk_2` FOREIGN KEY (`therapist_id`) REFERENCES `users` (`id`);

--
-- Restrições para tabelas `feedback`
--
ALTER TABLE `feedback`
  ADD CONSTRAINT `feedback_ibfk_1` FOREIGN KEY (`reflection_id`) REFERENCES `reflections` (`id`),
  ADD CONSTRAINT `feedback_ibfk_2` FOREIGN KEY (`therapist_approved_by`) REFERENCES `users` (`id`);

--
-- Restrições para tabelas `invitations`
--
ALTER TABLE `invitations`
  ADD CONSTRAINT `invitations_ibfk_1` FOREIGN KEY (`therapist_id`) REFERENCES `users` (`id`);

--
-- Restrições para tabelas `password_reset_tokens`
--
ALTER TABLE `password_reset_tokens`
  ADD CONSTRAINT `password_reset_tokens_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`);

--
-- Restrições para tabelas `reflections`
--
ALTER TABLE `reflections`
  ADD CONSTRAINT `fk_reflections_therapist` FOREIGN KEY (`therapist_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `reflections_ibfk_1` FOREIGN KEY (`client_id`) REFERENCES `users` (`id`);

--
-- Restrições para tabelas `therapist_clients`
--
ALTER TABLE `therapist_clients`
  ADD CONSTRAINT `therapist_clients_ibfk_1` FOREIGN KEY (`therapist_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `therapist_clients_ibfk_2` FOREIGN KEY (`client_id`) REFERENCES `users` (`id`);

--
-- Restrições para tabelas `user_push_tokens`
--
ALTER TABLE `user_push_tokens`
  ADD CONSTRAINT `fk_user_push_tokens_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
