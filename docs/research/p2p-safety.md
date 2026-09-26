# P2P ファイル共有の先行事例と、分散創造の安全性

| 項目 | 内容 |
| --- | --- |
| 調査日 | 2026-09-26 |
| 調査者 | Claude Opus 5.5 |
| 対象 | [concept.md](../concept.md)「過去との比較が足りない ― P2P ファイル共有ソフト」 |

## 1. 目的

分散創造は、素材と拡張機能を中央サーバーなしで配布する（[vision.md](../vision.md) 4.3）。同じく中央サーバーを持たなかった P2P ファイル共有ソフトの先例から、次の 4 つの問いに答える。

1. ソフトを開発・公開すること自体に、法的なリスクはあるか
2. Winny はなぜ廃れたか
3. マルウェアの拡散を防げるか。安全な素材や拡張機能だけを配布できるか
4. 利用者にとって不快なコンテンツを、利用者ごとに NG 設定できるか

## 2. 方法

- 判決文、官公庁・公的機関の公表資料、査読付き論文、公式の仕様書・文書を一次資料として用いた。
- すべての出典は、調査日に原文を取得し、引用した文が原文に存在することを照合した。引用は「」内に原文のまま示す。
- 引用中の空白は、原文の改行による折り返しを除いて原文どおりとした。
- 「3. 調査結果」には出典が述べる事実のみを書き、本プロジェクトとしての解釈は「4. 分散創造への示唆」に分けて書く。
- 法的な評価は筆者（AI）の調査に基づく整理であり、法律家による助言ではない。

## 3. 調査結果

### 3.1 ソフトの開発・公開と法的リスク（Winny 事件）

Winny の開発者は、Winny を公開・提供した行為が、利用者による著作権侵害（公衆送信権の侵害）の幇助にあたるとして起訴された。

**経過**：最高裁決定 [1] によれば、第 1 審は幇助犯の成立を認めて罰金 150 万円とした。控訴審（原判決）は幇助犯の成立を否定した。最高裁は、原判決の法令解釈には誤りがあるとしつつ、「被告人の行為につき著作権法違反罪の幇助犯の成立を否定したことは，結論において正当として是認できる」として、検察官の上告を棄却した（無罪確定）。

**ソフトの性質**：最高裁は Winny を「それ自体は多様な情報の交換を通信の秘密を保持しつつ効率的に行うことを可能とし，様々な分野に応用可能なソフトであるが，本件正犯者がしたように著作権を侵害する態様で利用することも可能なソフトである」と認定した [1]。

**判断の枠組み**：最高裁は、ソフトの公開・提供が幇助にあたるのは、次のいずれかの場合に限られるとした [1]。

- 「当該ソフトを利用して現に行われようとしている具体的な著作権侵害を認識，認容しながら，その公開，提供を行い，実際に当該著作権侵害が行われた場合」
- 「当該ソフトの性質，その客観的利用状況，提供方法などに照らし，同ソフトを入手する者のうち例外的とはいえない範囲の者が同ソフトを著作権侵害に利用する蓋然性が高いと認められる場合で，提供者もそのことを認識，認容しながら同ソフトの公開，提供を行い，実際にそれを用いて著作権侵害（正犯行為）が行われたとき」

**考慮された事情**：最高裁は、客観面について、関係証拠によれば「Ｗｉｎｎｙのネットワーク上を流通するファイルの４割程度が著作物で，かつ，著作権者の許諾が得られていないと推測されるもの」であったこと、提供方法が「ダウンロードをすることができる者について何ら限定をかけることなく，無償で，継続的に」公開するものであったことを挙げた [1]。一方、主観面について、開発者が「ウェブサイト上に違法なファイルのやり取りをしないよう求める注意書を付記したり，開発スレッド上にもその旨の書き込みをしたりして，常時，利用者に対し，Ｗｉｎｎｙを著作権侵害のために利用することがないよう警告を発していた」ことなどを考慮し、幇助の故意を認めなかった [1]。

**第 1 審の判断**：最高裁決定の要約によれば、第 1 審は、技術を外部へ提供する行為が違法かどうかは「その技術の社会における現実の利用状況やそれに対する認識，さらに提供する際の主観的態様いかんによる」とし、開発者が「新しいビジネスモデルが生まれることも期待して」侵害的な利用を認容していたと認定していた [1]。

**反対意見**：大谷剛彦裁判官は幇助犯が成立するとする反対意見を述べ、その中で「社会に広く無限定に技術を提供する以上，この面への相応の配慮をしつつ開発を進めることも，社会的な責任を持つ開発者の姿勢として望まれるところであろう」と述べた [1]。

### 3.2 Winny が廃れた経緯

**暴露ウイルス**：JPCERT/CC によれば、「2003年8月、ファイル共有ソフトウェア Winny を介して感染を広めるウイルス Antinny が現れ」た [2]。総務省は、Winny をインストールしたパソコンが Antinny に感染し、「パソコンに保存されていた個人情報をはじめとする重要な情報が流出するという事案が多発しています」と注意喚起した [3]。

**流出した情報は回収できない**：JPCERT/CC は「ファイル共有ネットワークに流出したファイルを完全に消去することは難しい」と述べている [2]。

**政府の呼びかけ**：JPCERT/CC によれば、「2006 年3月には安倍官房長官 (当時) が Winny の使用を控えるよう国民に呼びかけを行うという異例の事態」となった [2]。総務省も「情報の流出を防ぐために最も確実な対策はWinnyを利用しないこと」と述べた [3]。

**法改正**：文化庁の資料によれば、平成 21 年の著作権法改正により、私的使用目的であっても「違法にアップロードされたものと知りながら、権利者に無断で、音楽、映像をダウンロード（録音・録画）する行為を違法に」した（刑事罰はなし）[4]。平成 24 年の改正で、有償で提供されている音楽・映像の違法ダウンロードに「２年以下の懲役若しくは２００万円以下の罰金、又はこれの併科」の刑事罰が設けられ（親告罪）、平成 24 年 10 月 1 日に施行された [4]。令和 3 年 1 月 1 日からは、侵害コンテンツのダウンロード規制の対象が「音楽・映像から全ての著作物に拡大」された [5]。

**本調査で確認できなかったこと**：開発者の起訴が Winny の改良の継続に与えた影響、正規の配信サービスの普及との関係は、本調査の範囲では一次資料で確認できなかった。これらを Winny が廃れた理由として断定することは避ける。

### 3.3 P2P ネットワークでのマルウェアの拡散

**実測された感染率**：Kalafut らは、2 つの P2P ネットワーク（Limewire と OpenFT）を 1 か月以上計測し、「68% of all downloadable responses in Limewire containing archives and executables contain malware」、OpenFT では 3% であったと報告した [6]。また、「Most of the infections appear in zip and exe files」と報告している [6]。Shin らは KaZaA ネットワークで 50 万以上のファイルを調べ、「over 15% of the crawled files were infected by 52 different viruses」と報告した [7]。

**メモリ安全性**：Chromium プロジェクトは「Around 70% of our high severity security bugs are memory unsafety problems」と報告している（重大度が高い・致命的な 912 件の分析）[8]。

**サンドボックス**：WebAssembly の公式文書は、セキュリティモデルの目標の 1 つを「protect users from buggy or malicious modules」とし、「Each WebAssembly module executes within a sandboxed environment separated from the host runtime using fault isolation techniques」「Applications execute independently, and can't escape the sandbox without going through appropriate APIs」と述べている [9]。

### 3.4 利用者ごとの NG 設定（分散型 SNS の先例）

**Bluesky**：Bluesky と AT Protocol の設計論文は、ラベル付けを行うサービス（labeler）について「Users can choose in their client app which feeds and which labelers they want to use」と述べ、その利点として「Anyone can run such services, which enables a pluralistic ecosystem in which different parties may make different judgements about the same piece of content」を挙げている [10]。また、利用者はミュートする相手の一覧を公開でき、「other users can subscribe to that list, which has the same effect as if they individually muted all of the accounts on the list」と述べている [10]。

**Nostr**：Nostr の仕様 NIP-51 は、利用者が作れる一覧（リスト）を定義し、ミュートリスト（kind 10000）を「things the user doesn't want to see in their feeds」と定義している。対象は公開鍵・ハッシュタグ・単語・スレッドで、一覧の項目は公開にも非公開（暗号化）にもできる [11]。

**Mastodon**：Raman らは Mastodon の計測研究で、分散型のプラットフォームについて「empirically highlight a number of properties that are creating natural pressures towards recentralisation」と述べている [12]。

## 4. 分散創造への示唆

ここからは、調査結果を踏まえた本プロジェクトとしての解釈である。

### 4.1 開発・公開の法的リスク（問い 1）

- 最高裁の枠組み [1] では、ソフトが「価値中立」であることに加えて、**客観的な利用状況**、**提供方法**、**提供者の認識**が判断材料になる。
- 開発者が利用者に**違法な利用をしないよう常時警告していた**ことは、故意を否定する事情として考慮された [1]。分散創造でも、配布ページ・初回起動時・素材の公開時に、違法な利用をしないよう明示する（[vision.md](../vision.md) 6.2 と整合）。
- 第 1 審では、提供時の主観的な態様が有罪の根拠の一部になった [1]。プロダクトの公式文書では、違法な利用を勧める・期待すると読める表現を避ける。
- 大谷裁判官の反対意見 [1] は、開発者に「相応の配慮」を求めている。3.3・3.4 の安全策を最初から設計に組み込むことは、この観点からも意味がある。
- 最終的な判断は法律家に委ねるべきであり、一般公開の前に弁護士への相談を推奨する。

### 4.2 Winny の教訓（問い 2）

- 確認できた事実から言える最大の教訓は、**流出したデータは回収できない** [2][3] ことである。分散創造の素材も、一度公開すると取り消せない（[vision.md](../vision.md) 6.2）。公開前に内容を確認できる画面と、取り消せないことの明示が必要である。
- 暴露ウイルスは、利用者の端末上のファイルを勝手に共有フォルダへ置くことで被害を広げた [2][3]。分散創造では、**利用者が明示的に選んだ素材だけ**を公開し、作品フォルダや他のフォルダを自動で共有する仕組みを持たない。

### 4.3 マルウェア対策（問い 3）

- 計測研究では、感染は実行ファイルと圧縮ファイルに集中していた [6]。分散創造では、**素材**（画像などのデータ）と**拡張機能**（プログラム）でリスクが大きく異なる。
  - **素材**：データ形式を PNG などに限定し、読み込みにはメモリ安全な実装（Rust）を使う。重大な脆弱性の多くがメモリ安全性の問題である [8] ことから、効果が見込める。
  - **拡張機能**：WebAssembly のサンドボックスで実行し、ファイルやネットワークへのアクセスは利用者が許可した API に限る [9]（[vision.md](../vision.md) F-EXT-02〜04 と整合）。
- 「安全なものだけを配布する」ことは、中央の審査を持たない以上、保証できない。設計の目標を「危険なものが流れても、被害をサンドボックスの中に閉じ込める」に置く。

### 4.4 利用者ごとの NG 設定（問い 4）

- Bluesky のラベラーと共有ミュートリスト [10]、Nostr のミュートリスト [11] は、**中央が規制を強制せず、利用者が信頼する判断を選ぶ**仕組みの先例であり、[vision.md](../vision.md) 6.3 の方針と一致する。
- 分散創造では、次の 2 層を持つのが適当である。
  1. 自分用の NG リスト（作者の公開鍵・タグ・素材のハッシュ値）
  2. 信頼する人が公開した NG リストやラベルの購読（どれを購読するかは利用者が選ぶ）
- Mastodon の研究 [12] は、分散型でも再中央集権化の圧力が生じることを示している。人気のある NG リストの提供者が事実上の中央になりうるため、購読先を簡単に切り替えられる設計にする。

## 5. 未解決の問い

- 起訴が Winny の開発継続に与えた影響、配信サービスの普及との関係（一次資料が未確認）
- 分散創造の素材配布が、著作権法上どのように評価されうるか（法律家への相談が必要）
- NG リストの購読を、分散創造の P2P の仕組み（Iroh）の上でどう実現するか

## 参考文献

アクセス日はすべて 2026-09-26。

1. 最高裁判所第三小法廷. 平成21年(あ)第1900号 著作権法違反幇助被告事件 決定. 平成23年12月19日. 刑集65巻9号1380頁. https://www.courts.go.jp/assets/hanrei/hanrei-pdf-81846.pdf
2. JPCERT コーディネーションセンター. インターネットセキュリティの歴史 第21回「Antinny による情報漏えい多発」. 2008年10月1日. https://www.jpcert.or.jp/tips/2008/wr083801.html
3. 総務省. Winnyを介して感染するコンピュータウィルスによる情報流出に関する注意喚起. 平成18年4月11日. https://www.soumu.go.jp/main_sosiki/joho_tsusin/d_syohi/060411_1.html
4. 文化庁. 著作権法の一部を改正する法律の概要（平成24年改正）. https://www.bunka.go.jp/seisaku/chosakuken/hokaisei/h24_hokaisei/pdf/24_houkaisei_horitsu_gaiyou_ver6.pdf
5. 文化庁. 令和3年1月1日施行 侵害コンテンツのダウンロード違法化について. https://www.bunka.go.jp/seisaku/chosakuken/hokaisei/92735201.html
6. Kalafut, A., Acharya, A., & Gupta, M. (2006). A Study of Malware in Peer-to-Peer Networks. In *Proceedings of the 6th ACM SIGCOMM Conference on Internet Measurement (IMC '06)*, pp. 327–332. https://doi.org/10.1145/1177080.1177124 （本文：https://conferences.sigcomm.org/imc/2006/papers/p33-kalafut.pdf）
7. Shin, S., Jung, J., & Balakrishnan, H. (2006). Malware Prevalence in the KaZaA File-Sharing Network. In *Proceedings of the 6th ACM SIGCOMM Conference on Internet Measurement (IMC '06)*, pp. 333–338. https://doi.org/10.1145/1177080.1177125 （本文：http://conferences.sigcomm.org/imc/2006/papers/p34-shin.pdf）
8. The Chromium Projects. Memory safety. https://www.chromium.org/Home/chromium-security/memory-safety/
9. WebAssembly Community Group. Security. https://webassembly.org/docs/security/
10. Kleppmann, M., Frazee, P., Gold, J., Graber, J., Holmgren, D., Ivy, D., Johnson, J., Newbold, B., & Volpert, J. (2024). Bluesky and the AT Protocol: Usable Decentralized Social Media. In *Proceedings of the ACM CoNEXT-2024 Workshop on the Decentralization of the Internet (DIN '24)*. arXiv:2402.03239v2. https://arxiv.org/abs/2402.03239 （引用箇所：2.1 Moderation Features、3.4 Labelers and Feed Generators）
11. nostr-protocol. NIP-51: Lists. https://github.com/nostr-protocol/nips/blob/master/51.md
12. Raman, A., Joglekar, S., De Cristofaro, E., Sastry, N., & Tyson, G. (2019). Challenges in the Decentralised Web: The Mastodon Case. In *Proceedings of the 19th ACM Internet Measurement Conference (IMC '19)*. arXiv:1909.05801. https://arxiv.org/abs/1909.05801
