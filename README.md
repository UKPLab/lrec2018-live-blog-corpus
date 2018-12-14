# Live Blog Corpus for Summarization

In this project, we develop a corpus for Live Blog Summarization. This repository contains scripts to generate live blog summarization corpus using
The Guardian and BBC live blogs.

For a detailed description of this corpus please read:
[Live Blog Corpus for Summarization](https://tinyurl.com/yahqyhpn), P.V.S. et al., LREC 2018.

If you reuse this corpus and software, please use the following citation:

```
@inproceedings{TUD-CS-2018-0008,
	title = {Live Blog Corpus for Summarization},
	author = {P.V.S., Avinesh and Peyrard, Maxime and Meyer, Christian M.},
	organization = {Association for Computational Linguistics},
	booktitle = {Proceedings of the 11th International Conference on Language Resources and Evaluation (LREC)},
	pages = {to appear},
	Xmonth = may,
	year = {2018},
	location = {Miyazaki, Japan},
}
```
> **Abstract:** Live blogs are an increasingly popular news format to cover breaking news and live events in online journalism. 
Online news websites around the world are using this medium to give their readers a minute by minute update on an event.
Good summaries enhance the value of the live blogs for a reader but are often not available.
In this paper, we study a way of collecting corpora for automatic live blog summarization.
In an empirical evaluation using well-known state-of-the-art summarization systems, we show that live blogs corpus poses new challenges in the field of summarization.
We make our tools publicly available to reconstruct the corpus to encourage the research community and replicate our results. 

**Contact person:**
* Avinesh P.V.S., first_name AT aiphes.tu-darmstadt.de
* Maxime Peyrard, last_name AT aiphes.tu-darmstadt.de     
* http://www.ukp.tu-darmstadt.de/
* http://www.tu-darmstadt.de/

Don't hesitate to send us an e-mail or report an issue, if something is broken (and it shouldn't be) or if you have further questions.

> This repository contains experimental software and is published for the sole purpose of giving additional background details on the respective publication. 

## Download Processed Version

In case the script does not work you can also contact the authors for the processed data sets. This should help where the underlying links are not accessible.

### Prerequisites

* python >= 2.7 (tested with 2.7.6)

Installation
------------

1. Install required python packages.

```
pip install -r requirements.txt
```

2. Download ROUGE package from the [link](https://www.isi.edu/licensed-sw/see/rouge/) and place it in the rouge directory 

```
 python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

### Download URLs

For BBC, install selenium package and download [chrome driver](https://sites.google.com/a/chromium.org/chromedriver/) to crawl ajax links.

```
mkdir driver
cp chromedriver driver/
```

To download the processed (or) raw URLs:

```
python generate_data.py --corpus=[guardian/bbc] --mode=download --data_type=[processed/raw]
```

### Run the Baseline

To run the baseline systems and get scores:

```
python summarize/baseline.py -d guardian -l english
python utils/aggregate_baselines.py -d guardian
```

### Fetch URLs

To fetch the URLS of the guardian and BBC liveblogs:

```
python generate_data.py --corpus=[guardian/bbc] --mode=fetch_urls 
```

