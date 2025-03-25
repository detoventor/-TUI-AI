import os
import json
import requests
from rich import print
from rich.console import Console
from rich.panel import Panel
from typing import Dict, List

# URL-адреса API (убрал бесплатные версии, оставил только структуру)
# url_meta = "https://api.meta.ai/v1/llama/3.3/70B/instruct/turbo/free"
# url_deepseek = "https://api.deepseek.ai/v1/DeepSeek-R1-Distill-Llama-70B-free"

console = Console()

# Константы
API_KEY_FILE = "api_key.json"
CHAT_HISTORY_FILE = "chat_history.json" # Файл для сохранения истории чатов
API_KEY_URL_HELP = "https://platform.together.ai/settings/api-keys"  # Замените на правильную ссылку.  Этот URL - пример от togetherAI


class ChatSession:
    """
    Класс для управления сессией чата с нейросетью.
    """

    def __init__(self, model_name: str, api_key: str, history: List[Dict[str, str]] | None = None):
        """
        Инициализирует сессию чата.

        Args:
            model_name: Название модели нейросети.
            api_key: API-ключ.
            history: Начальная история чата (если есть).
        """
        self.model_name = model_name
        self.api_key = api_key
        self.history: List[Dict[str, str]] = history if history is not None else [] # История чата

    def send_message(self, prompt: str) -> str:
        """
        Отправляет сообщение нейросети и возвращает ответ.

        Args:
            prompt: Сообщение пользователя.

        Returns:
            Ответ нейросети.
        """
        from together import Together

        client = Together(api_key=self.api_key)
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[*self.history, {"role": "user", "content": prompt}],
            )
            answer = response.choices[0].message.content
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": answer})
            return answer
        except Exception as e:
            print(f"Ошибка при отправке запроса: {e}")
            return "Произошла ошибка при обработке запроса."

    def display_history(self):
        """
        Выводит историю сообщений чата.
        """
        console.print("[bold]История чата:[/bold]")
        for message in self.history:
            role = message["role"]
            content = message["content"]
            console.print(f"[{'bold blue' if role == 'user' else 'bold green'}]{role.capitalize()}:[/] {content}")


def load_api_key() -> str | None:
    """Загружает API-ключ из файла."""
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r") as f:
            try:
                data = json.load(f)
                return data.get("api_key")
            except json.JSONDecodeError:
                console.print("[red]Ошибка: Некорректный JSON формат в файле api_key.json. Пожалуйста, проверьте файл.[/red]")
                return None
    return None


def save_api_key(api_key: str):
    """Сохраняет API-ключ в файл."""
    with open(API_KEY_FILE, "w") as f:
        json.dump({"api_key": api_key}, f)


def get_api_key() -> str:
    """Получает API-ключ от пользователя или из файла."""
    api_key = load_api_key()

    if not api_key:
        console.print("[yellow]API-ключ не найден.[/yellow]")
        console.print(f"[yellow]Пожалуйста, укажите ваш API-ключ.  Вы можете получить его здесь: {API_KEY_URL_HELP}[/yellow]")
        api_key = input("Введите ваш API-ключ: ")
        save_api_key(api_key)
        console.print("[green]API-ключ сохранен.[/green]")
    return api_key


def load_chat_history() -> Dict[str, List[Dict[str, str]]]:
    """Загружает историю чатов из файла."""
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                console.print("[red]Ошибка: Некорректный JSON формат в файле chat_history.json. История чатов будет сброшена.[/red]")
                return {}
    return {}


def save_chat_history(chat_history: Dict[str, List[Dict[str, str]]]):
    """Сохраняет историю чатов в файл."""
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(chat_history, f, indent=4) # Добавил indent для читаемости


def main():
    console.print(Panel("[bold]Добро пожаловать в программу для общения с нейросетями![/bold]"))

    api_key = get_api_key()
    if not api_key:
        console.print("[red]API-ключ не предоставлен.  Программа не может работать без API-ключа.[/red]")
        return

    chat_history = load_chat_history() # Загружаем историю чатов
    chat_sessions: Dict[str, ChatSession] = {}  # Словарь для хранения сессий чата

    # Восстанавливаем сессии чатов на основе сохраненной истории
    for chat_name, history in chat_history.items():
        # Определяем модель, которая использовалась в чате (предполагаем, что она не менялась)
        # todo:  Добавить логику, чтобы можно было менять модель
        if history:
            try:
                first_message = history[0]
                if first_message["role"] == "system" and "model" in first_message:
                    model_name = first_message["model"]
                else:
                    model_name = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free" # Стандартная модель, если не указана
            except (KeyError, IndexError):
                model_name = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
        else:
            model_name = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"  # Стандартная модель, если нет истории

        chat_sessions[chat_name] = ChatSession(model_name, api_key, history)



    current_chat: str | None = None  # Имя текущей сессии чата

    try: # Добавляем блок try-finally для сохранения истории при выходе
        while True:
            if current_chat:
                console.print(f"[bold]Текущий чат: {current_chat}[/bold]")
            else:
                console.print("[bold]Главное меню[/bold]")

            if not current_chat:
                console.print("[bold]Выберите действие:[/bold]")
                console.print("1. Создать новый чат")
                console.print("2. Выбрать существующий чат")
                console.print("3. Выход")

                choice = input("> ")

                if choice == "1":
                    chat_name = input("Введите имя для нового чата: ")
                    console.print("[bold]Выберите нейросеть:[/bold]")
                    console.print("1. Meta Llama (meta-llama/Llama-3.3-70B-Instruct-Turbo-Free)")
                    console.print("2. DeepSeek (deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free)")
                    model_choice = input("> ")

                    if model_choice == "1":
                        model_name = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
                    elif model_choice == "2":
                        model_name = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free"
                    else:
                        console.print("[bold]Недопустимый выбор модели.[/bold]")
                        continue

                    chat_sessions[chat_name] = ChatSession(model_name, api_key)
                    current_chat = chat_name
                    console.print(f"[green]Чат '{chat_name}' создан и активирован.[/green]")


                elif choice == "2":
                    if not chat_sessions:
                        console.print("[yellow]Нет доступных чатов. Создайте новый чат.[/yellow]")
                        continue

                    console.print("[bold]Доступные чаты:[/bold]")
                    for name in chat_sessions:
                        console.print(f"- {name}")

                    chat_name = input("Введите имя чата для выбора: ")
                    if chat_name in chat_sessions:
                        current_chat = chat_name
                        console.print(f"[green]Чат '{chat_name}' активирован.[/green]")
                    else:
                        console.print("[red]Чат с таким именем не найден.[/red]")

                elif choice == "3":
                    break  # Выход из программы
                else:
                    console.print("[bold]Недопустимый выбор.[/bold]")


            else:  # Мы находимся в сессии чата
                chat_session = chat_sessions[current_chat]

                console.print("Введите ваше сообщение (или 'menu'/'back' для возврата в главное меню, 'history' для просмотра истории): ")
                prompt = input("> ")

                if prompt.lower() in ["menu", "back"]:
                    current_chat = None  # Возвращаемся в главное меню
                    continue  # Начинаем следующий цикл while

                if prompt.lower() == "history":
                    chat_session.display_history()
                    continue  # Начинаем следующий цикл while

                response = chat_session.send_message(prompt)
                console.print(Panel(f"[bold]Ответ:[/bold]\n{response}"))

    finally: # Сохраняем историю перед выходом
        # Сохраняем историю всех чатов
        chat_history = {name: session.history for name, session in chat_sessions.items()}
        save_chat_history(chat_history)
        console.print("[green]История чатов сохранена.[/green]")


if __name__ == "__main__":
    main()