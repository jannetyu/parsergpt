# parserGPT
import argparse
import os
import sys
import time
import openai
import json
import pandas as pd
import snowflake.connector
#from snowflake.snowpark.sql import *
#from snowpark import Session



#multiline comment for spec
"""
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
"""

# now the app itself

# set up the parser
parser = argparse.ArgumentParser(description='ParserGPT')
parser.add_argument('--upc', type=str, help='UPC to search for')
parser.add_argument('--product_name', type=str, help='Product Name to search for')
parser.add_argument('--full_record', type=str, help='Full Record to search for')

# parse the args
args = parser.parse_args()

# example of command line command
# python main.py --upc 065743234112

# does it have to have a UPC or product name?
if args.upc is None and args.product_name is None:
    print("You must specify a UPC or Product Name")
    #sys.exit(1)

# set up the snowflake connection
SNOWFLAKE_USER = os.environ.get('SNOWFLAKE_USER')
SNOWFLAKE_PASSWORD = os.environ.get('SNOWFLAKE_PASSWORD')
SNOWFLAKE_ACCOUNT = os.environ.get('SNOWFLAKE_ACCOUNT')
SNOWFLAKE_DATABASE ="CONSOLIDATED"
SNOWFLAKE_SCHEMA="PUBLIC"
SNOWFLAKE_WAREHOUSE="COMPUTE_WH"
SNOWFLAKE_ROLE="SYSADMIN"

conn = snowflake.connector.connect(
    user=SNOWFLAKE_USER,
    password=SNOWFLAKE_PASSWORD,
    account=SNOWFLAKE_ACCOUNT,
    warehouse=SNOWFLAKE_WAREHOUSE,
    database=SNOWFLAKE_DATABASE,
    schema=SNOWFLAKE_SCHEMA
    )

cur = conn.cursor()
print(str(args.upc))
# get the data from outSnowflake and put it into a dataframe

# get a single record
'''
select "product_upc","product_name", "item_ingredients_list", "active_ingredients" from CONSOLIDATED.PUBLIC."v2_consolidated_ss_columns" where "product_upc" = '{str(args.upc)}' limit 1
'''

# get a bunch of records
'''select distinct "product_upc","product_name", "item_ingredients_list", "active_ingredients" from CONSOLIDATED.PUBLIC."v2_consolidated_ss_columns" where "item_ingredients_list" is not null and "product_upc" is not null limit 10'''
outSnowflake = cur.execute(f'''select "product_upc","product_name", "item_ingredients_list", "active_ingredients" from CONSOLIDATED.PUBLIC."v2_consolidated_ss_columns" where "product_upc" = '{str(args.upc)}' limit 1''')
if outSnowflake is not None:
  df = pd.DataFrame(outSnowflake.fetchall())
else:
  df = pd.DataFrame()
df.columns = ['product_upc', 'product_name', 'item_ingredients_list', 'active_ingredients']
#print(df)

# just get the ingredients list as string
ingredientsList = df['item_ingredients_list'][0]
print("raw ingredients list:")
print(ingredientsList)

print("product upc:")
upc = df['product_upc'][0]
print(upc)

print("product name:")
product_name = df['product_name'][0]
print(product_name)

# set up the openai connection
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
source='dataRecord' #or image if parsing images

dataPrompt=f'''Parse the following list of ingredients by UPC for upc {upc} from the packaging of a consumer packaged goods. Only get valid ingredients, do not include words like "ingredients".   Extract the name of the ingredient, the unit, and the amount and type whether active or inactive. If active or inactive is not declared, assume active.  If units is not present assume 'n/a' and if amount is not present assume 0.  List my indicate a serving concept like "In Each Tablet" or "per spray" - include this as servingIndicator. Include the source as {source}.  Include in a notes field anything that seemed odd, if anything.

Return results as JSON:
{{"{upc}":
    {{"ingredients":[
                    {{
                    "name":"value",
                    "unit":"valueUnit",
                    "amount":"valueAmount",
                    "type","activeOrInactive",
                    "source",{source}
                    }},
                    {{...}}
        ]}},
        "notes":"anything that needs to be looked at by a human",
        "serveringIndicator":"valueServingIndicator"
    }}

here is the ingredients list:
{ingredientsList}

'''

completion = openai.ChatCompletion.create(
  model="gpt-3.5-turbo",
  temperature=0,
  messages=[
    {"role": "system", "content": "You are a helpful data parser."},
    {"role": "user", "content": f'{dataPrompt}'}
  ]
)

print("openai response:")
# print this pretty json
#print(json.dumps(completion, indent=4, sort_keys=True))
print(completion.choices[0].message.content)
