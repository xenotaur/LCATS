from sentence_transformers import SentenceTransformer
from cosine_similarity import compute_cosine_similarity


model = SentenceTransformer("all-MiniLM-L6-v2")
texts = [
    "The canine barked loudly.",
    "The dog made a noisy bark.",
    "He ate a lot of pizza.",
    "He devoured a large quantity of pizza pie.",
]

text_embeddings = model.encode(texts)

text_embeddings_dict = dict(zip(texts, list(text_embeddings)))

dog_text_1 = "The canine barked loudly."
dog_text_2 = "The dog made a noisy bark."
cs1 = compute_cosine_similarity(text_embeddings_dict[dog_text_1],
                          text_embeddings_dict[dog_text_2])

pizza_text_1 = "He ate a lot of pizza."
pizza_test_2 = "He devoured a large quantity of pizza pie."
cs2 = compute_cosine_similarity(text_embeddings_dict[pizza_text_1],
                          text_embeddings_dict[pizza_test_2])

cs3 = compute_cosine_similarity(text_embeddings_dict[dog_text_1],
                          text_embeddings_dict[pizza_text_1])

#type(text_embeddings)
#text_embeddings.shape
