"""Authors and their archives.

To ADD an author: append a dict with a unique `key`, display `name`, fetch
`kind` ("pg" for plain static HTML like paulgraham.com, or "wp" for WordPress —
also give its `api_url`), and an ordered `essays` list of {title, url}.
To REMOVE an author: delete their dict. To stop sending but keep history, just
remove the dict — rotation state for missing authors is ignored.

Essays are sent in list order, never repeating, until an author's list is
exhausted, then it recycles from the top.
"""

AUTHORS = [
    {
        "key": "paul_graham",
        "name": "Paul Graham",
        "kind": "pg",
        "essays": [
            {"title": "Startup = Growth", "url": "https://paulgraham.com/growth.html"},
            {"title": "Do Things that Don't Scale", "url": "https://paulgraham.com/ds.html"},
            {"title": "How to Get Startup Ideas", "url": "https://paulgraham.com/startupideas.html"},
            {"title": "What We Look for in Founders", "url": "https://paulgraham.com/founders.html"},
            {"title": "Black Swan Farming", "url": "https://paulgraham.com/swan.html"},
            {"title": "How to Convince Investors", "url": "https://paulgraham.com/convince.html"},
            {"title": "The 18 Mistakes That Kill Startups", "url": "https://paulgraham.com/startupmistakes.html"},
            {"title": "How to Make Wealth", "url": "https://paulgraham.com/wealth.html"},
            {"title": "Relentlessly Resourceful", "url": "https://paulgraham.com/relres.html"},
            {"title": "Startups in 13 Sentences", "url": "https://paulgraham.com/13sentences.html"},
            {"title": "Default Alive or Default Dead?", "url": "https://paulgraham.com/aord.html"},
            {"title": "The Anatomy of Determination", "url": "https://paulgraham.com/determination.html"},
            {"title": "Maker's Schedule, Manager's Schedule", "url": "https://paulgraham.com/makersschedule.html"},
            {"title": "How to Start a Startup", "url": "https://paulgraham.com/start.html"},
            {"title": "How to Think for Yourself", "url": "https://paulgraham.com/think.html"},
        ],
    },
    {
        "key": "bill_gurley",
        "name": "Bill Gurley",
        "kind": "wp",
        "api_url": "https://abovethecrowd.com/wp-json/wp/v2/posts",
        "essays": [
            {"title": "All Markets Are Not Created Equal", "url": "https://abovethecrowd.com/2012/11/13/all-markets-are-not-created-equal-10-factors-to-consider-when-evaluating-digital-marketplaces/"},
            {"title": "All Revenue is Not Created Equal: The Keys to the 10X Revenue Club", "url": "https://abovethecrowd.com/2011/05/24/all-revenue-is-not-created-equal-the-keys-to-the-10x-revenue-club/"},
            {"title": "The Dangerous Seduction of the Lifetime Value (LTV) Formula", "url": "https://abovethecrowd.com/2012/09/04/the-dangerous-seduction-of-the-lifetime-value-ltv-formula/"},
            {"title": "How to Miss By a Mile: An Alternative Look at Uber's Potential Market Size", "url": "https://abovethecrowd.com/2014/07/11/how-to-miss-by-a-mile-an-alternative-look-at-ubers-potential-market-size/"},
            {"title": "Money Out of Nowhere: How Internet Marketplaces Unlock Economic Wealth", "url": "https://abovethecrowd.com/2019/02/27/money-out-of-nowhere-how-internet-marketplaces-unlock-economic-wealth/"},
            {"title": "The Thing I Love Most About Uber", "url": "https://abovethecrowd.com/2018/04/19/the-thing-i-love-most-about-uber/"},
            {"title": "On the Road to Recap", "url": "https://abovethecrowd.com/2016/04/21/on-the-road-to-recap/"},
            {"title": "Why Facebook Clearly Belongs in the 10X Revenue Club", "url": "https://abovethecrowd.com/2012/02/01/why-facebook-clearly-belongs-in-the-10x-revenue-club/"},
        ],
    },
    {
        "key": "andrew_chen",
        "name": "Andrew Chen",
        "kind": "wp",
        "api_url": "https://andrewchen.com/wp-json/wp/v2/posts",
        "essays": [
            {"title": "The Law of Shitty Clickthroughs", "url": "https://andrewchen.com/the-law-of-shitty-clickthroughs/"},
            {"title": "Growth Hacker is the new VP Marketing", "url": "https://andrewchen.com/how-to-be-a-growth-hacker-an-airbnbcraigslist-case-study/"},
            {"title": "The Next Feature Fallacy", "url": "https://andrewchen.com/the-next-feature-fallacy-the-fallacy-that-the-next-new-feature-will-suddenly-make-people-use-your-product/"},
            {"title": "New data shows losing 80% of mobile users is normal", "url": "https://andrewchen.com/new-data-shows-why-losing-80-of-your-mobile-users-is-normal-and-that-the-best-apps-do-much-better/"},
            {"title": "Minimize your Time to Product/Market Fit", "url": "https://andrewchen.com/ttpmf-time-to-product-market-fit/"},
            {"title": "Zero to Product/Market Fit", "url": "https://andrewchen.com/zero-to-productmarket-fit-presentation/"},
            {"title": "What to do when growth stalls", "url": "https://andrewchen.com/growth-stalls/"},
        ],
    },
]
