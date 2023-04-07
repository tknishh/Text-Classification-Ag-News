# -*- coding: utf-8 -*-
"""notebook.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/16ZKLV_jbhTO8vdtGaj7ywdwRHeeECgYd

# 1. Install important dependencies
"""

# # Install necessary packages
!pip install transformers nltk datasets numpy seaborn pandas scikit-learn matplotlib

"""# 2. Import Dependencies"""

import pandas as pd
import os
import seaborn as sns
from matplotlib import pyplot as plt
from sklearn.model_selection import train_test_split

# To import the Transformer Models
from transformers import AutoTokenizer, DataCollatorWithPadding
from transformers import AutoModelForSequenceClassification, TrainingArguments, Trainer

# to convert to Dataset datatype - the transformers library does not work well with pandas
from datasets import Dataset

"""### 2.1 Load the dataset"""

# The dataset does not contain class labels, so we need to explicitly provide it
df=pd.read_csv("/content/train.csv")
df.head()

df = df.rename(columns={'Class Index':'label'})
df.head()

"""### 2.2 Data statistics"""

# checking for unbalanced dataset
plt.style.use('fivethirtyeight')
plt.figure(figsize=(8,4))
sns.countplot(x=df['label'])
plt.show()

"""### 2.3 Check for null values"""

df.info()

"""# 3. Data Preprocessing"""

# concatinating the 'title' and 'description' column
df['text']=(df['Title']+df['Description'])
df.drop(columns=['Title','Description'],axis=1,inplace=True)
df.head()

# Text before preprocessing - contains symbols like ()\-,.' which is not useful
df['text'][1]

"""### 3.1 Remove Punctuations"""

import re   # regular expression can be used to remove any punctuation or unnecessary symbols

def remove_punctuations(text):
     text=re.sub(r'[\\-]',' ',text)
     text=re.sub(r'[,.?;:\'(){}!|0-9]','',text)
     return text

# the apply method applies a function along an axis of dataframe
df['text']=df['text'].apply(remove_punctuations)
df.head()

import nltk

# downloading corpus only would work
nltk.download()

"""### 3.2 Remove StopWords"""

from nltk.corpus import stopwords

# english stopwords
stopw=stopwords.words('english')
stopw[:10]

def remove_stopwords(text):
    clean_text=[]
    for word in text.split(' '):
        if word not in stopw:
            clean_text.append(word)
    return ' '.join(clean_text)

# remove stopwords
df['text']=df['text'].apply(remove_stopwords)

# the class label in dataset contains labels as 1,2,3,4 but the model needs 0,1,2,3, so we subtract 1 from all
df['label']=df['label'].apply(lambda x:x-1)
df.head()

df['text'][1]   # this is the final preprocessed text

"""### 3.3 Split the data into training and testing sets"""

from sklearn.model_selection import train_test_split

# since training on the full dataset(120,000 samples) would be take so long, the train size is only taken to be 30%
train_df,test_df=train_test_split(df[['text','label']],train_size=.3,shuffle=True)
test_df=test_df[:10000]

train_df.shape,test_df.shape    # training set has 36000 samples and testing set has 10000 samples

"""### 3.4 Load a pre-built tokenizer and convert to tokens"""

# load tokenizer from bert base uncased model available from huggingface.co
model_name='bert-base-uncased'
tokenizer=AutoTokenizer.from_pretrained(model_name)

def preprocess_function(examples):
    """
    Tokenizes the given text

    input -> dataset (columns = text, label)
    output -> tokenized dataset (columns = text, label, input, attention)
    """
    return tokenizer(examples["text"], truncation=True)

def pipeline(dataframe):
    """
    Prepares the dataframe so that it can be given to the transformer model
    
    input -> pandas dataframe
    output -> tokenized dataset (columns = text, label, input, attention)
    """    
    # This step isn't mentioned anywhere but is vital as Transformers library only seems to work with this Dataset data type
    dataset = Dataset.from_pandas(dataframe, preserve_index=False)
    tokenized_ds = dataset.map(preprocess_function, batched=True)
    tokenized_ds = tokenized_ds.remove_columns('text')
    return tokenized_ds

# create pipeline for training data and testing data
tokenized_train = pipeline(train_df)
tokenized_test = pipeline(test_df)

"""# 4. Load a pre-trained model

### 4.1 Adjust Model training arguments
"""

# load bert-based-uncased model for fine tuning
data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=4)

# adjust the training arguments
training_args = TrainingArguments(
    output_dir="./results",
    save_strategy = 'epoch',
    optim='adamw_torch',
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
)

# create the trainer from Trainer class in transformer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_test,
    tokenizer=tokenizer,
    data_collator=data_collator,
)

"""### 4.2 Train the model"""

trainer.train()

model_loss=pd.read_csv('loss.csv')
plt.figure(figsize=(12,5))
plt.plot(model_loss['Step'],model_loss['Training Loss'],label='loss',marker='o')
plt.xlabel('Step')
plt.ylabel('Loss value')
plt.legend()
plt.title('Model Loss Trend')
plt.show()

"""### 4.3 Evaluate the Model"""

# create tokenized text for test dataset
tokenized_test = pipeline(test_df)
tokenized_test = tokenized_test.remove_columns('label')

# input the tokenized text to the trainer to get predictions
preds = trainer.predict(tokenized_test)

import numpy as np
from sklearn.metrics import classification_report,confusion_matrix

# the maximum value in the prediction is the predicted class label
preds_flat = [np.argmax(x) for x in preds[0]]

# The model got a precision of 96%, 97%, 90% and 89% on class labels 0,1,2,3 and similarly for recall, f1-score, support
print(classification_report(test_df['label'], preds_flat))  # accuracy: 93%

plt.figure(figsize=(10,8))

# plot the heat map 
sns.heatmap(
    confusion_matrix(test_df['label'], preds_flat),
    annot=True,
    xticklabels=['World','Sport','Business','Sci/Tech'],
    yticklabels=['World','Sport','Business','Sci/Tech'],
    cmap=plt.cm.magma_r
)
plt.title('Confusion Matrix')
plt.show()

"""### 4.4 Test model on random predictions"""

import random

num=random.randint(0,len(test_df)-101)
tokenized_test = pipeline(test_df[num:num+100]).remove_columns('label')

# accuracy on random 100 samples from test dataset: 99% which is great!
preds=trainer.predict(tokenized_test)
preds_flat = [np.argmax(x) for x in preds[0]]
print(classification_report(test_df['label'][num:num+100], preds_flat))

"""### 4.5 Manually compare predictions on sample test data"""

class_labels=['World','Sports','Business','Sci/Tech']

num=random.randint(0,len(test_df)-1)
tokenized_test = pipeline(test_df[num:num+10]).remove_columns('label')
preds=trainer.predict(tokenized_test)
preds_flat = [np.argmax(x) for x in preds[0]]

# generating predicted class and actual class for 10 random samples from test dataset
print('Prediction\tActual\n----------------------')
for i in range(len(preds_flat)):
    print(class_labels[preds_flat[i]],' ---> ',class_labels[test_df['label'].values[num+i]])

"""# 5. Save Model"""

# save_model method saves the model along with its metadata in the specified path
trainer.save_model('models')

"""# 6. Load Model"""

# for loading model, we just need to specify the path of the folder for saved model
model = AutoModelForSequenceClassification.from_pretrained('models')
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_test,
    tokenizer=tokenizer,
    data_collator=data_collator,
)

