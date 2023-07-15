# parserGPT

a GPT inspired/built parser of many things

## HOW TO DO THIS YOURSELF

### a specification for writing code faster with AI and your brai

* set up a github repository
* include a readme.md and gitignore
* fill out a rough spec for your piece of software
* think of the spec in terms of it being a good prompt for GPT and for a human
* turn the repository into a github Codespace
* open the repository and codespace in Visual Studio Code or Visual Studio Code Insiders Edition
* Make sure you have Github Copilot and Github Copilot Labs and Github Copilot Chat
* use github secrets to stash your environment variables you want available to code spaces (you could, of course use other python venv ways of doing this)
* once you do all the above once in your life it becomes so much easier for every project you'll do for the most popular programming language work

## Specification for ParserGPT App

### Functional Overview Description

This is a simply python based application that will retrieve Snowflake Database data, parse and transform it with OpenAI Chat API, and expose the functionality in a python flask powered webpage with a simple form for retrieving a Snowflake record by UPC or Product Name fuzzy match.

### Detailed Functional Specifications

* The snowflake database table houses simple, but messy, Consumer Packaged Goods records with their ingredients, packaging nutrition label images and packaging label marketing images
* the parser will use the ingredients field, the nutrition labels and packaging labels to form a complete list of ingredients and marketing claims and normalize and validate all listed ingredients and marketing claims.
* this normalization will happen by using GPT to extract the ingredients and claims, normalizing their strings/characters and validating against GPT and a customer approved ingredient names and claims list
* to parse the images will use a suitable python library (like opencv + openAI clip etc) to classify for presence of ingredients and then OCR for text extraction and then parse using the previos parser
* the same idea will be used for marketing claims as for ingredients.  both are just usually words printed on a package in obvious list form, and they all get on the package and into the image from a database so there's a high correlation to already validated data.
* the python flask web app will simply provide an input form for UPC or product name, return a single record that best matches the input and use the record to pass to the parsing and normalizing.
* a secondary option in the python flask web app is to allow the input of a full record that may not be in the database
* the web app should return the results of parsing in JSON form for use in other processing tasks

### Data table and record information

#### SQL Statement to get base records for UPC and Ingredients

`select distinct "product_upc","product_name", "item_ingredients_list", "active_ingredients" from CONSOLIDATED.PUBLIC."v2_consolidated_ss_columns" where "item_ingredients_list" is not null and "product_upc" is not null`

##### Record Examples

as a TSV

```

product_upc	product_name	item_ingredients_list	active_ingredients
065743234112	Live Clean Fresh Water Hydrating Body Wash 12 fl. oz. Squeeze Bottle	Water (Aqua), Sodium Lauryl Sulfoacetate, Cocamidopropyl Betaine, Sodium Methyl 2-Sulfolaurate, Sodium Chloride, Lavandula Angustifolia (Lavender) Extract (Certified Organic), Chamomilla Recutita (Matricaria) Flower Extract (Certified Organic), Rosmarinus Officinalis (Rosemary) Leaf Extract (Certified Organic), Camellia Sinensis Leaf Extract (Certified Organic), Panthenol, Sodium Hyaluronate, Tocopheryl Acetate, Disodium 2-Sulfolaurate, Hydroxypropyl Methylcellulose, Glycol Distearate, Glycerin, Phenoxyethanol, Ethylhexylglycerin, Potassium Sorbate, Sodium Benzoate, Hexyl Cinnamal, Limonene, Linalool, Fragrance (Parfum), Citric Acid.	
023400016136	Soft Scrub Cleanser with Bleach 36 oz	" Ingredients: Sodium Hypochlorite 1.1%, Other Ingredients: 98.9%, Total 100.0%."

```


#### SQL Statement to get the base records for UPC, product packaging including marketing claims, supplemental and nutrition images

`select distinct upc, brand, producttitle, imagesection from LABEL_INSIGHTS_TEST.PUBLIC.LABEL_INSIGHT_GTIN14;`

##### Example Record

as a plaintext with JSON

```

UPC
041497434657

BRAND
WEIS QUALITY

PRODUCTTITLE
CREAM CAFFEINE FREE SODA

IMAGESECTION
{
  "images": [
    {
      "colorSpace": "SRGB",
      "format": "PSD",
      "url": "https://vsion-images.labelinsight.com/products/20045/images/041497434657-TOPC031584MarketingA1C1-830b5bfc-d985-4496-a2c9-ff96fa7b325e.psd"
    },
    {
      "colorSpace": "SRGB",
      "format": "PNG",
      "url": "https://vsion-images.labelinsight.com/products/20045/images/041497434657-TOPC031584MarketingA1C1-830b5bfc-d985-4496-a2c9-ff96fa7b325e.png"
    },
    {
      "colorSpace": "SRGB",
      "format": "TIF",
      "url": "https://vsion-images.labelinsight.com/products/20045/images/041497434657-TOPC031584MarketingA1C1-830b5bfc-d985-4496-a2c9-ff96fa7b325e.tif"
    }
  ]
}

```

*** Note that it would be tempting to join tables etc... but UPCs and product names might need to be cleaned up between tables to successfully get the exact matches.  proceed with caution

#### Snowflake details

`pip install snowflake-snowpark-python`
`pip install "snowflake-snowpark-python[pandas]"`
`pip install snowflake-connector-python`

* note that snowpark and connector are slightly different things.  snowpark will run things snowflakes python stuff (fancy).  connector just gets you access to the databases

more here if you need it [Snowflake Python Docs](https://docs.snowflake.com/en/developer-guide/snowpark/python/setup)

##### Connection

[Python Snowflake Querying](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-example#querying-data)

```

import snowflake.connector

conn = snowflake.connector.connect(
    user=USER,
    password=PASSWORD,
    account=ACCOUNT,
    warehouse=WAREHOUSE,
    database=DATABASE,
    schema=SCHEMA
    )

cur = conn.cursor()
cur.execute('select distinct "product_upc","product_name", "item_ingredients_list", "active_ingredients" from CONSOLIDATED.PUBLIC."v2_consolidated_ss_columns" where "item_ingredients_list" is not null and "product_upc" is not null')

```

#### OpenAI API Connecting and Prompt

[OpenAI API](https://platform.openai.com/docs/api-reference/chat)

##### Chat API Call
```

import os
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")

source='dataRecord' #or image if parsing images

dataPrompt=f'''Parse the following list of ingredients by UPC from the packaging of a consumer packaged goods. Only get valid ingredients, do not include words like "ingredients".   Extract the name of the ingredient, the unit, and the amount and type whether active or inactive. If active or inactive is not declared, assume active.  If units is not present assume 'n/a' and if amount is not present assume 0.  Include the source of {source}.  Include in a notes field anything that seemed odd, if anything.

Return results as JSON:
{"UPC":
    {"ingredients":[
                    {
                    "name":"value",
                    "unit":"valueUnit",
                    "amount":"valueAmount",
                    "type","activeOrInactive",
                    "source","imageOrTextField"
                    },
                    {...}
        ],
        "notes":"anything that needs to be looked at by a human"
    }
}
'''

completion = openai.ChatCompletion.create(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "system", "content": "You are a helpful data parser."},
    {"role": "user", "content": f'{dataPrompt}'}
  ]
)

print(completion.choices[0].message)


```