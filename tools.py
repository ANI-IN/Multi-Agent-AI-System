"""
Tools module for the multi-agent system.
Defines all tools for both the music catalog and invoice information sub-agents.
"""

import ast
import logging
from langchain_core.tools import tool
from database import get_db

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Music Catalog Tools
# ─────────────────────────────────────────────

@tool
def get_albums_by_artist(artist: str) -> str:
    """Get albums by an artist from the music catalog."""
    try:
        db = get_db()
        result = db.run(
            f"""
            SELECT Album.Title, Artist.Name
            FROM Album
            JOIN Artist ON Album.ArtistId = Artist.ArtistId
            WHERE Artist.Name LIKE '%{artist}%';
            """,
            include_columns=True,
        )
        if not result or result.strip() == "[]":
            return f"No albums found for artist: {artist}"
        return result
    except Exception as e:
        logger.error(f"Error in get_albums_by_artist: {e}")
        return f"Error looking up albums for '{artist}'. Please try again."


@tool
def get_tracks_by_artist(artist: str) -> str:
    """Get songs/tracks by an artist (or similar artists) from the catalog."""
    try:
        db = get_db()
        result = db.run(
            f"""
            SELECT Track.Name as SongName, Artist.Name as ArtistName
            FROM Album
            LEFT JOIN Artist ON Album.ArtistId = Artist.ArtistId
            LEFT JOIN Track ON Track.AlbumId = Album.AlbumId
            WHERE Artist.Name LIKE '%{artist}%'
            LIMIT 20;
            """,
            include_columns=True,
        )
        if not result or result.strip() == "[]":
            return f"No tracks found for artist: {artist}"
        return result
    except Exception as e:
        logger.error(f"Error in get_tracks_by_artist: {e}")
        return f"Error looking up tracks for '{artist}'. Please try again."


@tool
def get_songs_by_genre(genre: str) -> str:
    """Fetch songs from the database that match a specific genre."""
    try:
        db = get_db()
        genre_id_query = f"SELECT GenreId FROM Genre WHERE Name LIKE '%{genre}%'"
        genre_ids_raw = db.run(genre_id_query)

        if not genre_ids_raw or genre_ids_raw.strip() == "[]":
            return f"No songs found for the genre: {genre}"

        genre_ids = ast.literal_eval(genre_ids_raw)
        genre_id_list = ", ".join(str(gid[0]) for gid in genre_ids)

        songs_query = f"""
            SELECT Track.Name as SongName, Artist.Name as ArtistName
            FROM Track
            LEFT JOIN Album ON Track.AlbumId = Album.AlbumId
            LEFT JOIN Artist ON Album.ArtistId = Artist.ArtistId
            WHERE Track.GenreId IN ({genre_id_list})
            GROUP BY Artist.Name
            LIMIT 8;
        """
        songs = db.run(songs_query, include_columns=True)

        if not songs or songs.strip() == "[]":
            return f"No songs found for the genre: {genre}"

        formatted_songs = ast.literal_eval(songs)
        result_list = [
            {"Song": song["SongName"], "Artist": song["ArtistName"]}
            for song in formatted_songs
        ]
        return str(result_list)
    except Exception as e:
        logger.error(f"Error in get_songs_by_genre: {e}")
        return f"Error looking up songs for genre '{genre}'. Please try again."


@tool
def check_for_songs(song_title: str) -> str:
    """Check if a song exists in the catalog by its name."""
    try:
        db = get_db()
        result = db.run(
            f"""
            SELECT Track.Name, Artist.Name as ArtistName, Album.Title as AlbumTitle
            FROM Track
            LEFT JOIN Album ON Track.AlbumId = Album.AlbumId
            LEFT JOIN Artist ON Album.ArtistId = Artist.ArtistId
            WHERE Track.Name LIKE '%{song_title}%'
            LIMIT 10;
            """,
            include_columns=True,
        )
        if not result or result.strip() == "[]":
            return f"No songs found matching: {song_title}"
        return result
    except Exception as e:
        logger.error(f"Error in check_for_songs: {e}")
        return f"Error looking up song '{song_title}'. Please try again."


# ─────────────────────────────────────────────
# Invoice Information Tools
# ─────────────────────────────────────────────

@tool
def get_invoices_by_customer_sorted_by_date(customer_id: str) -> str:
    """
    Look up all invoices for a customer using their ID.
    Returns invoices sorted by date (most recent first).
    """
    try:
        db = get_db()
        return db.run(
            f"SELECT * FROM Invoice WHERE CustomerId = {customer_id} ORDER BY InvoiceDate DESC;"
        )
    except Exception as e:
        logger.error(f"Error in get_invoices_by_customer_sorted_by_date: {e}")
        return f"Error retrieving invoices for customer {customer_id}. Please try again."


@tool
def get_invoices_sorted_by_unit_price(customer_id: str) -> str:
    """
    Look up all invoices for a customer, sorted by unit price from highest to lowest.
    Useful when customer wants to know about a specific invoice based on cost.
    """
    try:
        db = get_db()
        return db.run(
            f"""
            SELECT Invoice.*, InvoiceLine.UnitPrice
            FROM Invoice
            JOIN InvoiceLine ON Invoice.InvoiceId = InvoiceLine.InvoiceId
            WHERE Invoice.CustomerId = {customer_id}
            ORDER BY InvoiceLine.UnitPrice DESC;
            """
        )
    except Exception as e:
        logger.error(f"Error in get_invoices_sorted_by_unit_price: {e}")
        return f"Error retrieving invoices for customer {customer_id}. Please try again."


@tool
def get_employee_by_invoice_and_customer(invoice_id: str, customer_id: str) -> str:
    """
    Find the employee associated with a specific invoice and customer.
    Returns employee name, title, and email.
    """
    try:
        db = get_db()
        result = db.run(
            f"""
            SELECT Employee.FirstName, Employee.Title, Employee.Email
            FROM Employee
            JOIN Customer ON Customer.SupportRepId = Employee.EmployeeId
            JOIN Invoice ON Invoice.CustomerId = Customer.CustomerId
            WHERE Invoice.InvoiceId = {invoice_id} AND Invoice.CustomerId = {customer_id};
            """,
            include_columns=True,
        )
        if not result or result.strip() == "[]":
            return f"No employee found for invoice ID {invoice_id} and customer ID {customer_id}."
        return result
    except Exception as e:
        logger.error(f"Error in get_employee_by_invoice_and_customer: {e}")
        return f"Error finding employee for invoice {invoice_id}. Please try again."


# Tool lists for easy access
music_tools = [get_albums_by_artist, get_tracks_by_artist, get_songs_by_genre, check_for_songs]
invoice_tools = [get_invoices_by_customer_sorted_by_date, get_invoices_sorted_by_unit_price, get_employee_by_invoice_and_customer]
