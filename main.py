import json
import time

import html2text
from fastapi import FastAPI, HTTPException

h = html2text.HTML2Text()
h.ignore_links = True
from mistralai import Mistral
from typing import List

app = FastAPI()

mistral_client = Mistral(api_key="wldp0chTgdyU6dgGQ2AmWT8Kb0kNXgVW")

clause_knowledge = json.load(open("Clause_Knowledge_0828_dirty.json", 'r'))
all_tags = json.load(open("all_tags.json", 'r'))
sol_and_cont = json.load(open("Solicitation and Contract.json", 'r', encoding='utf-8'))
all_clauses = sol_and_cont["Clauses"]




def get_section_clauses(selected_section, selected_subclause, filtered_titles):
    clauses = []
    for section in all_clauses:
        if section["Name"] == selected_section:
            if section["SubClauses"]:
                for subclause in section["SubClauses"]:
                    #WHEN TOGLE IS OFF A SUBCLAUSE IS SENT
                    if selected_subclause:
                        if subclause["Name"] == selected_subclause:
                            for alt in subclause["Alternatives"]:
                                # if not alt["IsAdditional"] and alt["TemplateIdSector"] is None and alt["AlternativeClientReferenceId"] not in ["Heading"]:
                                if alt["AlternativeClientReferenceId"] not in ["Heading"]:
                                    clause_name = alt["Name"]
                                    clause_id = alt["Id"]
                                    clause_text = h.handle(alt["Content"])
                                    if filtered_titles:
                                        if clause_id in filtered_titles:
                                            clauses.append(f"Clause Name: {clause_name}\n\nClause Content: {clause_text}")
                                    else:
                                        clauses.append(f"Clause Name: {clause_name}\n\nClause Content: {clause_text}")
                    else:
                        for alt in subclause["Alternatives"]:
                            # if not alt["IsAdditional"] and alt["TemplateIdSector"] is None and alt["AlternativeClientReferenceId"] not in ["Heading"]:
                            if alt["AlternativeClientReferenceId"] not in ["Heading"]:
                                clause_name = alt["Name"]
                                clause_id = alt["Id"]
                                clause_text = h.handle(alt["Content"])
                                if filtered_titles:
                                    if clause_id in filtered_titles:
                                        clauses.append(f"Clause Name: {clause_name}\n\nClause Content: {clause_text}")
                                else:
                                    clauses.append(f"Clause Name: {clause_name}\n\nClause Content: {clause_text}")
            for alt in section["Alternatives"]:
                # if not alt["IsAdditional"] and alt["TemplateIdSector"] is None and alt["AlternativeClientReferenceId"] not in ["Heading"]:
                if alt["AlternativeClientReferenceId"] not in ["Heading"]:
                    clause_name = alt["Name"]
                    clause_id = alt["Id"]
                    clause_text = h.handle(alt["Content"])
                    if filtered_titles:
                        if clause_id in filtered_titles:
                            clauses.append(f"Clause Name: {clause_name}\n\nClause Content: {clause_text}")
                    else:
                        clauses.append(f"Clause Name: {clause_name}\n\nClause Content: {clause_text}")
    return clauses


# ---------------------------------------------------


@app.post("/filter")
async def filter_clauses(input_string: str, clauses: List[int], section: str, subclause):
    try:

        clause = get_section_clauses(section, subclause, clauses)

        # Load the knowledge from a JSON file
        per_clause_knowledge  = get_clause_knowledge(clauses)

        # Call the filter_helper function with provided data and loaded knowledge
        result = filter_helper(input_string, clause , per_clause_knowledge)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# The refactored filter_helper function
def filter_helper(input_string: str, clause_names: List[str], per_clause_knowledge: List[str]):
    all_answers = ""

    if input_string:
        system = f"""
        You are a procurement officer and have to consult the user on the CLAUSES based on MANUAL.
        Answer exactly to the questions of the user. You have to always answer to the user's questions.
        
        If the users asks for table, always create a table based on the distinguishing characteristics of the CLAUSES.
        Create as many columns with distinguishing elements of the CLAUSES, as possible.
        
        Always use the KNOWLEDGE below and provide only the copy of the clauses as they are provided in the KNOWLEDGE!
        [KNOWLEDGE]\n
        CLAUSES: {clause_names}\n
        MANUAL: {per_clause_knowledge}
        [/KNOWLEDGE]

        Provide output in a following json structure:
        {{"answer": "answer or introductory text without any fragment from the table", "table": "table always in List of Dictionaries format, if user asks to provide a table, or else empty string"}}
        
        Make sure the json is valid!
        """

        prompt = f"{input_string}"
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]

        while True:
            try:
                # Replace mistral_client with the actual client you use to interact with Mixtral AI
                chat_response = mistral_client.chat.complete(
                    model="open-mixtral-8x7b",
                    response_format={"type": "json_object"},
                    messages=messages,
                )

                output_str = chat_response.choices[0].message.content
                output = json.loads(output_str)

                message_to_print = output["answer"]
                table_to_print = output.get("table", "")

                all_answers = f"{message_to_print}\nTable{table_to_print}"

            except Exception as error:
                print(">", error)
                time.sleep(10)
                continue
            break

    return all_answers


def get_clause_knowledge(clause_ids: List[int]):
    per_clause_knowledge = []
    for section in clause_knowledge["section"]:
        for subclause in section["subclause"]:
            for clause in subclause["clause"]:
                if clause["id"] in clause_ids:
                    for similar in clause["similars"]:
                        if f"""{similar["title"]}\n{similar["text"]}""" not in per_clause_knowledge:
                            per_clause_knowledge.append(f"""{similar["title"]}\n{similar["text"]}""")
    return per_clause_knowledge









# ------------------------------------------------------------------
@app.post("/section_tags")
def get_section_tags(alternative_names: List[str], selected_section: str, selected_subclause: str):
    all_tags_of_section = all_tags[selected_section]
    relevant_question_tags = {}

    if selected_subclause == "All":
        for question, clause_tags in all_tags_of_section.items():
            tags_to_add = []
            for clause, tags in clause_tags.items():
                for tag in tags:
                    if tag not in tags_to_add:
                        tags_to_add.append(tag)
            relevant_question_tags[question] = tags_to_add
    else:
        for alt_name in alternative_names:
            for question, clause_tags in all_tags_of_section.items():
                if question not in relevant_question_tags:
                    relevant_question_tags[question] = []
                for clause, tags in clause_tags.items():
                    if clause == alt_name:
                        for tag in tags:
                            if tag not in relevant_question_tags[question]:
                                relevant_question_tags[question].append(tag)

    return relevant_question_tags


@app.post("/filter_by_tags")
def filter_dict_by_tags(data_dict, tags):
    title_per_question = {}
    for (question, sub_dict_1), sub_dict_2 in zip(data_dict.items(), tags.values()):
        all_q_tags = []
        for q_tags in sub_dict_1.values():
            all_q_tags.extend(q_tags)
        title_per_question[question] = []
        for title, tags in sub_dict_1.items():
            tag_exists = all(item in tags for item in sub_dict_2)
            if tag_exists:
                title_per_question[question].append(title)
    first_question = list(title_per_question.keys())[0]
    common_values = set(title_per_question[first_question])  # Initialize with the first list's values as a set
    for key in title_per_question:
        common_values.intersection_update(title_per_question[key])
    common_values = list(common_values)

    return common_values