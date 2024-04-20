import openai
import nextcord
from nextcord.ext import commands
import asyncio

# Set up bot
client = nextcord.Client(intents=nextcord.Intents.all())
bot = commands.Bot(command_prefix="!", intents=nextcord.Intents.all())

conversations = {} # Initialize conversations dictionary


# Configure OpenAI API
openai.api_key = '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'


# Event: Bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print('Bot is ready')


INSTRUCTIONS = """You are Unibot! You are designed to help students in a University. Your goal is to provide 
information and give further context to the users questions, answering them as if you were a lecturer. To get 
started, please tell how I can assist you, and I will provide you with the best personalized information. If you have 
any questions relating to academics or general advice, including history, course topics and general guidance feel 
free to ask me. If you have questions or topics outside of this scope, please note that I can only answer questions 
related to the afformentioned. Questions that are not related to education or general guidance will not be answered 
but instead be addressed with an error message. This is some additional information, Madam Ruth and Mr. Aryettey can be found on the Eest Wing second floor of the faculty. The level 100 students will always have their exams on the North Wing First Floor. All students register at the Administration."""

TEMPERATURE = 0.5
MAX_TOKENS = 500
FREQUENCY_PENALTY = 0
PRESENCE_PENALTY = 0.6
# limits how many questions we include in the prompt
MAX_CONTEXT_QUESTIONS = 10

previous_questions_and_answers = []



def get_response(instructions, previous_questions_and_answers, new_question):
    """Get a response from ChatCompletion

    Args:
        instructions: The instructions for the chatbot - this determines how it will behave
        previous_questions_and_answers: Chat history
        new_question: The new question to ask the bot

    Returns:
        The response text
    """
    # build the messages
    messages = [
        {"role": "system", "content": instructions},
    ]
    # add the previous questions and answers
    for question, answer in previous_questions_and_answers[-MAX_CONTEXT_QUESTIONS:]:
        messages.append({"role": "user", "content": question})
        messages.append({"role": "assistant", "content": answer})
    # add the new question
    messages.append({"role": "user", "content": new_question})

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        top_p=1,
        frequency_penalty=FREQUENCY_PENALTY,
        presence_penalty=PRESENCE_PENALTY,
    )
    return completion.choices[0].message.content


def get_moderation(question):
    """
    Check if the question is safe to ask the model

    Parameters:
        question (str): The question to check

    Returns a list of errors if the question is not safe, otherwise returns None
    """

    errors = {
        "hate": "Content that expresses, incites, or promotes hate based on race, gender, ethnicity, religion, "
                "nationality, sexual orientation, disability status, or caste.",
        "hate/threatening": "Hateful content that also includes violence or serious harm towards the targeted group.",
        "self-harm": "Content that promotes, encourages, or depicts acts of self-harm, such as suicide, cutting, "
                     "and eating disorders.",
        "sexual": "Content meant to arouse sexual excitement, such as the description of sexual activity, "
                  "or that promotes sexual services (excluding sex education and wellness).",
        "sexual/minors": "Sexual content that includes an individual who is under 18 years old.",
        "violence": "Content that promotes or glorifies violence or celebrates the suffering or humiliation of others.",
        "violence/graphic": "Violent content that depicts death, violence, or serious physical injury in extreme "
                            "graphic detail.",
    }
    response = openai.Moderation.create(input=question)
    if response.results[0].flagged:
        # get the categories that are flagged and generate a message
        result = [
            error
            for category, error in errors.items()
            if response.results[0].categories[category]
        ]
        return result
    return None



# Command: !chat
@bot.command()
async def chat(ctx):
    if nextcord.utils.get(ctx.author.roles, name='Student') is None:
        await ctx.send("You do not have the necessary permissions to use this command.")
    else:
        if ctx.author.id not in conversations:
            conversations[ctx.author.id] = []

        await ctx.author.send("Welcome to Unibot! How can I assist you?")
        await ctx.author.send("Please enter your message.")

        def check(message):
            return message.author == ctx.author and isinstance(message.channel, nextcord.DMChannel)

        try:
            while True:
                user_input = await bot.wait_for('message', timeout=500.0, check=check)
                conversations[ctx.author.id].append(user_input.content)

                question = user_input.content

                # Check if the question is safe
                errors = get_moderation(question)
                if errors:
                    error_message = "Sorry, your question didn't pass the moderation check:\n"
                    error_message += "\n".join(errors)
                    await ctx.author.send(error_message)
                    continue

                # Handle assignment-related questions
                if "assignment" in question.lower():
                    await assignment(ctx)
                    return
                # Get the response from ChatCompletion
                response = get_response(INSTRUCTIONS, previous_questions_and_answers, question)

                # Add the new question and answer to the list of previous questions and answers
                previous_questions_and_answers.append((question, response))

                await ctx.author.send(response)  # Send the generated response


        except TimeoutError:

            await ctx.author.send("No response received. Ending the conversation.")


        finally:

            del conversations[ctx.author.id]


@bot.command()
async def assignment(ctx: commands.Context):
    student_role = nextcord.utils.get(ctx.guild.roles, name="Student")

    department_options = ["IT", "Business", "Arts"]
    department_choice = await get_user_choice(ctx.author, "Choose a department:", department_options)

    while True:
        if department_choice == "IT":
            level_options = ["Level 100", "Level 200", "Level 300", "Level 400"]
            level_choice = await get_user_choice(ctx.author, "Choose a level:", level_options)

        if level_choice == "Level 100":
            course_options = ["Literature", "Introduction to Maths"]
            course_choice = await get_user_choice(ctx.author, "Choose a course:", course_options)

            if course_choice == "Literature":
                description = "This is the assignment description for Literature."
                due_date = "Due date: May 30, 2023"
            elif course_choice == "Introduction to Maths":
                description = "This is the assignment description for Introduction to Maths."
                due_date = "Due date: June 5, 2023"
            else:
                description = "Invalid course selection."
                due_date = ""

            await ctx.author.send(f"Assignment Details:\n{description}\n{due_date}")

        # Ask if the user wants to continue
        continue_choice = await get_user_choice(ctx.author, "Do you want to continue?", ["Yes", "No"])
        if continue_choice == "No":
            break
        else:
            await ctx.author.send("Invalid department selection.")
            break

    await ctx.author.send("Assignment details have been retrieved. You are now back to the chat command.")
    await asyncio.sleep(1)  # Wait for a short duration before processing the chat command again
    await bot.process_commands(ctx.message)  # Process the chat command again


async def get_user_choice(ctx, prompt, options):
    option_string = "\n".join(f"{index}. {option}" for index, option in enumerate(options, start=1))
    prompt_message = f"{prompt}\n{option_string}\nPlease enter the number of your choice:"
    await ctx.send(prompt_message)

    while True:
        try:
            choice_message = await bot.wait_for("message", timeout=60)
            choice = int(choice_message.content)
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                await ctx.send("Invalid choice. Please enter a valid number.")
        except ValueError:
            await ctx.send("Invalid choice. Please enter a valid number.")
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond.")
            return


# Run the bot
bot.run("MTA2ODUyMDk5OTI0ODc0NDUwOA.GzbZXo.ok189E8rnxkqUYOC8ugbgLxgoK0mEkb5F6QUCw")
