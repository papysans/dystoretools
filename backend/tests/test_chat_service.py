import pytest

from dystore.chat.service import add_message, create_conversation, list_conversations, list_messages


@pytest.mark.asyncio
async def test_conversation_and_messages_persist(session) -> None:
    conversation = await create_conversation(session, title="Test")
    await add_message(session, conversation_id=conversation.id, role="user", content="hello")
    await add_message(session, conversation_id=conversation.id, role="assistant", content="world", tokens_in=1, tokens_out=2)

    conversations = await list_conversations(session)
    messages = await list_messages(session, conversation.id)

    assert conversations[0].title == "Test"
    assert conversations[0].total_tokens_in == 1
    assert len(messages) == 2
    assert messages[1].content == "world"
