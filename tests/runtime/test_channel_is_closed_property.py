"""Test for ChannelEndpoint.is_closed() method (v1.25.4 fix).

This test verifies the fix for the bug where ChannelEndpoint.is_closed()
was a property instead of a method, causing "'bool' is not callable" error.

Bug: Documentation said ch.is_closed() but implementation was @property,
so calling it as a method tried to call a bool value.

Fix: Changed is_closed from @property to a regular method for consistency
with other Channel methods (send(), receive(), close(), cancel()).
"""

import pytest
from helen.runtime.channel import Channel, ChannelEndpoint


class TestChannelEndpointIsClosed:
    """Test ChannelEndpoint.is_closed() method."""

    def test_is_closed_method_exists(self):
        """ChannelEndpoint should have is_closed() method."""
        ch = Channel("test")
        ep = ChannelEndpoint(ch, is_main_thread=True)

        # Should not raise AttributeError
        assert hasattr(ep, 'is_closed')
        assert callable(ep.is_closed)
        assert isinstance(ep.is_closed(), bool)

    def test_is_closed_initial_state(self):
        """is_closed() should return False initially."""
        ch = Channel("test")
        ep = ChannelEndpoint(ch, is_main_thread=True)

        assert ep.is_closed() is False
        assert ch.is_closed() is False

    def test_is_closed_after_close(self):
        """is_closed() should return True after close()."""
        ch = Channel("test")
        ep = ChannelEndpoint(ch, is_main_thread=True)

        ep.close()

        assert ep.is_closed() is True
        assert ch.is_closed() is True

    def test_is_closed_after_cancel(self):
        """is_closed() should return True after cancel()."""
        ch = Channel("test")
        ep = ChannelEndpoint(ch, is_main_thread=True)

        ep.cancel()

        assert ep.is_closed() is True
        assert ch.is_closed() is True

    def test_is_closed_consistency_with_method(self):
        """is_closed() method should be consistent with is_channel_closed() method."""
        ch = Channel("test")
        ep = ChannelEndpoint(ch, is_main_thread=True)

        # Before close
        assert ep.is_closed() == ep.is_channel_closed()

        # After close
        ep.close()
        assert ep.is_closed() == ep.is_channel_closed()

    def test_is_closed_both_endpoints(self):
        """Both endpoints should see the same closed state."""
        ch = Channel("test")
        main_ep = ChannelEndpoint(ch, is_main_thread=True)
        spawned_ep = ChannelEndpoint(ch, is_main_thread=False)

        # Initially both open
        assert main_ep.is_closed() is False
        assert spawned_ep.is_closed() is False

        # Close from main endpoint
        main_ep.close()

        # Both should see closed
        assert main_ep.is_closed() is True
        assert spawned_ep.is_closed() is True

    def test_is_closed_method_vs_call_method(self):
        """Direct method call should match call_method behavior."""
        ch = Channel("test")
        ep = ChannelEndpoint(ch, is_main_thread=True)

        # Both should return the same value
        assert ep.is_closed() == ep.call_method("is_closed", [])

        ep.close()
        assert ep.is_closed() == ep.call_method("is_closed", [])
