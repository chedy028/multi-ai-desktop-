from app.panes.base_pane import BasePane

class ChatGPTPane(BasePane):
    """Pane for interacting with ChatGPT using QWebEngineView."""
    URL = "https://chat.openai.com"
    JS_INPUT = "#prompt-textarea"
    JS_SEND_BUTTON = "button[data-testid='send-button']"
    JS_LAST_REPLY = "div[data-message-author-role='assistant'] .markdown"

    def __init__(self, parent=None):
        super().__init__(parent)
        # All other methods (like send_prompt) are inherited from BasePane.

    def send_prompt(self, prompt_text: str):
        self._ensure_driver()
        if not self.driver:
            self.answer_display.setPlainText("WebDriver not available.")
            return
        try:
            input_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.JS_INPUT))
            )
            input_field.clear() # Clear any previous text
            input_field.send_keys(prompt_text)
            
            # Wait for send button to be clickable and click it
            send_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.JS_SEND_BUTTON))
            )
            send_button.click()
            
            # Wait for the response to appear
            # This requires careful selection of the element that indicates a new response
            # We might need to count existing assistant messages and wait for a new one.
            num_existing_replies = len(self.driver.find_elements(By.CSS_SELECTOR, self.JS_LAST_REPLY))
            
            WebDriverWait(self.driver, 60).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, self.JS_LAST_REPLY)) > num_existing_replies and \
                          d.find_elements(By.CSS_SELECTOR, self.JS_LAST_REPLY)[-1].text.strip() != ""
            )
            
            # Get the last reply
            all_replies = self.driver.find_elements(By.CSS_SELECTOR, self.JS_LAST_REPLY)
            ai_response = all_replies[-1].text if all_replies else "No response found."
            
            self.answer_display.setPlainText(ai_response)
            self.answerReady.emit(ai_response)
            
        except TimeoutException:
            err_msg = "Timeout waiting for ChatGPT response."
            self.answer_display.setPlainText(err_msg)
            self.answerReady.emit(err_msg)
            print(err_msg)
        except Exception as e:
            err_msg = f"Error interacting with ChatGPT: {str(e)}"
            self.answer_display.setPlainText(err_msg)
            self.answerReady.emit(err_msg)
            print(err_msg)

    def clear_response(self):
        super().clear_response() # Clears the QTextEdit
        if self.driver:
            try:
                # Try to click a "new chat" button or navigate to the base URL
                # This depends on the specific UI of the chat service
                new_chat_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, self.NEW_CHAT_BUTTON))
                )
                new_chat_button.click()
                # Wait for the input field to be ready again
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.JS_INPUT))
                )
            except (TimeoutException, NoSuchElementException) as e:
                print(f"ChatGPT: Could not find or click new chat button, attempting URL reload: {e}")
                if self.URL:
                    self.driver.get(self.URL)
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, self.JS_INPUT))
                    )
            except Exception as e:
                print(f"Error trying to start new chat/clear on ChatGPT: {e}")
    
    def __del__(self):
        """Clean up the WebDriver when the pane is destroyed."""
        try:
            self.driver.quit()
        except:
            pass 