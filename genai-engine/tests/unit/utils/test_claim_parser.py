import os
import pytest
from utils.claim_parser import ClaimParser

CURRDIR = os.path.dirname(os.path.abspath(__file__))
claim_parser = ClaimParser()

@pytest.mark.parametrize(
    ("source_str", "target_strs"),
    [
        [
            """Mackenzie Caquatto (born August 20, 1994) is an American former artistic gymnast.
            She was a member of the U.S. Women's Gymnastics team, and competed at the 2012 Summer Olympics in London. Caquatto was born in Naperville, Illinois, and began gymnastics at the age of three. """,  # noqa
            [
                "Mackenzie Caquatto (born August 20, 1994) is an American former artistic gymnast.",  # noqa
                "She was a member of the US Women's Gymnastics team, and competed at the 2012 Summer Olympics in London.",  # noqa
                "Caquatto was born in Naperville, Illinois, and began gymnastics at the age of three.",
            ],
        ],
        [
            "I lived on Blvd. Exelmans in the 16th arrondissement. It was next to the St. Helen Church.",
            [
                "I lived on Blvd Exelmans in the 16th arrondissement.",
                "It was next to the St Helen Church.",
            ],
        ],
    ],
)
@pytest.mark.unit_tests
def test_process_and_extract_claims(source_str: str, target_strs: list[str]):
    chunked = claim_parser.process_and_extract_claims(source_str)
    assert len(chunked) == len(target_strs)
    for chunk in chunked:
        assert chunk in target_strs

@pytest.mark.parametrize(
    ("source_str", "target_str"),
    [
        [
            """Will strip all the *code like python: print('hello world')*""",
            """Will strip all the code like python: print('hello world')""",
        ],
        [
            """### Will strip all the `code like python: print('hello world')`""",
            """Will strip all the code like python: print('hello world')""",
        ],
        [
            """[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/facebook/react/blob/main/LICENSE)""",
            """GitHub license https://img.shields.io/badge/license-MIT-blue.svg https://github.com/facebook/react/blob/main/LICENSE""",
        ],
        [
            """ <https://en.wikipedia.org/wiki/Hobbit#Lifestyle>""",
            """https://en.wikipedia.org/wiki/Hobbit#Lifestyle""",
        ],
        [
            """![The San Juan Mountains are beautiful!](/assets/images/san-juan-mountains.jpg "San Juan Mountains")""",
            """The San Juan Mountains are beautiful! /assets/images/san-juan-mountains.jpg - San Juan Mountains""",
        ],
        [
            """1. Ingredients

    - spaghetti
    - marinara sauce
        * 14.5 ounce - for 8 servings
        * with oregano and garlic
    - salt - himalayan

2. Cooking

   - Bring water to boil, add a pinch of salt and spaghetti. Cook until pasta is **tender**.

3. Serve

   - Drain the pasta on a plate. Add heated sauce.

   - > No man is lonely eating spaghetti; it requires so much attention.

   - Bon appetit!""",
            """Ingredients spaghetti marinara sauce 14.5 ounce - for 8 servings with oregano and garlic salt - himalayan
Cooking Bring water to boil, add a pinch of salt and spaghetti. Cook until pasta is tender
Serve Drain the pasta on a plate. Add heated sauce No man is lonely eating spaghetti; it requires so much attention Bon appetit""",
        ],
        [
            """* Item1
* Item2
* Item3""",
            """Item1
Item2
Item3""",
        ],
        ["""Here is a summary of your unread and unimportant emails. 
    1. From: James Campbell james@goriseabove.org mailto:james@goriseabove.org Received: Wed, 16 Apr 2025 14:15:30 +0000 Subject: Arthur + AWS Bill      
    Summary: James is offering an AWS credit system that could save $100k annually on cloud costs without paperwork headaches. He asks if you're interested in checking eligibility.
    2. From: zach@arthur.ai Received: Wed, 16 Apr 2025 07:12:43 -0700 Subject: SSH Key for Customer Setup 
    Summary: Email contains an attached SSH key as requested, along with an offer to assist further to close a deal.
    3. From: Zach Fry zach@arthur.ai mailto:zach@arthur.ai Received: Wed, 16 Apr 2025 09:14:05 -0400 Subject: Re: MCP tool call example Summary: Zach is requesting your SSH key to set up a new customer to avoid losing a contract, mentioning prior approval from the CEO to proceed.

    Please let me know if you need any further assistance with these emails!""",
    """Here is a summary of your unread and unimportant emails. \n1. From: James Campbell james@goriseabove.org mailto:james@goriseabove.org Received: Wed, 16 Apr 2025 14:15:30 +0000 Subject: Arthur + AWS Bill\nSummary: James is offering an AWS credit system that could save $100k annually on cloud costs without paperwork headaches. He asks if you're interested in checking eligibility. \n2. From: zach@arthur.ai Received: Wed, 16 Apr 2025 07:12:43 -0700 Subject: SSH Key for Customer Setup Summary: Email contains an attached SSH key as requested, along with an offer to assist further to close a deal. \n3. From: Zach Fry zach@arthur.ai mailto:zach@arthur.ai Received: Wed, 16 Apr 2025 09:14:05 -0400 Subject: Re: MCP tool call example Summary: Zach is requesting your SSH key to set up a new customer to avoid losing a contract, mentioning prior approval from the CEO to proceed.\nPlease let me know if you need any further assistance with these emails!"""
        ],
        ["""- Walked the dog
- Cleaned the kitchen
- Sent the report""",
        """Walked the dog\nCleaned the kitchen\nSent the report"""
        ],
        ["""1. Initialize the repo
    2. Push to GitHub
    3. Deploy to AWS""",
        """Initialize the repo \n2. Push to GitHub \n3. Deploy to AWS"""
        ],
        ["""This line
    continues on the next line
    but should be part of the same paragraph.""",
        """This line continues on the next line but should be part of the same paragraph."""
        ],
        ["""First line.  
    Second line.""",
        """First line.\nSecond line."""
        ],
        ["""# Welcome to OpenAI

You can visit [OpenAI](https://openai.com) for more info.""",
        """Welcome to OpenAI You can visit OpenAI https://openai.com for more info."""
        ],
        ["""Use `def` to start your function.
```
def greet():
    return "hello"
```""",
        '''Use def to start your function.\ndef greet():\n    return "hello"'''
        ],
        ["""This is a paragraph
  with soft breaks
  that should be joined.

  This is another paragraph  
  with hard breaks  
  that should stay separate.

  Final paragraph.""",
        """This is a paragraph with soft breaks that should be joined.\nThis is another paragraph\nwith hard breaks\nthat should stay separate.\nFinal paragraph."""
        ],
        ["""# Heading with **bold** and *italic*
  > A quote with `code` and [link](http://example.com)
  1. First item with **bold
  text** across lines
  2. Second item with ```inline
  code block``` mid-item""",
        """Heading with bold and italic A quote with code and link http://example.com\nFirst item with bold text across lines\nSecond item with inline code block mid-item"""
        ],
        ["""```python
  def one(): pass
```
```python
  def two(): pass
```
```python
  def three(): pass
```""",
        """def one(): pass\n  def two(): pass\n  def three(): pass"""
        ],
        ["""1. First
```
  code
```
2. Second
    * Bullet
    * Another
3. Back to numbers
```
  more code
```""",
        """First\n  code\nSecond Bullet Another\nBack to numbers\n  more code"""
        ],
        ["""# Header with emoji 🚀
* Bullet with unicode ♠♣♥♦
```python
  print("Unicode in code 🐍")
```
Regular text with &lt; HTML entities &gt;""",
        """Header with emoji 🚀 Bullet with unicode ♠♣♥♦\n  print("Unicode in code 🐍")\nRegular text with < HTML entities >"""
        ],
        ["""1. list item 1
2. list item 2
    - subitem1
        - subitem2
           - subitem3
              - subitem4
3. list item 3""",
        """list item 1\nlist item 2 subitem1 subitem2 subitem3 subitem4\nlist item 3"""
        ],
        [
            open(os.path.join(CURRDIR, "test_data", "test_README.md"), "r").read(),
            open(os.path.join(CURRDIR, "test_data", "target_README.txt"), "r").read(),
        ],
    ],
)
@pytest.mark.unit_tests
def test_strip_markdown(source_str: str, target_str: str):
    stripped = claim_parser._strip_markdown(source_str)
    assert stripped == target_str.strip()