import copy
import datetime

import pytest
from helper.lang import busy_assert_eq, busy_wait_for, one_moment
from helper.torrent import make_torrent_files, make_torrent_single, temporary_torrents

from aioqbt import exc
from aioqbt.api import AddFormBuilder
from aioqbt.api.types import (
    Category,
    FilePriority,
    InfoFilter,
    PieceState,
    TorrentInfo,
    TorrentProperties,
    TorrentState,
)
from aioqbt.client import APIClient


@pytest.mark.asyncio
async def test_add(client: APIClient):
    up_limit = 111**1
    dl_limit = 333**1
    category = "add-category"
    savepath = "somewhere/there"

    sample = make_torrent_single("add")
    now = datetime.datetime.now()

    await client.torrents.add(
        AddFormBuilder.with_client(client)
        .savepath(savepath)
        .cookie("dummy=empty")
        .rename("add-renamed")
        .root_folder(True)
        .paused(True)
        .skip_checking(False)  # skip checking cause first last piece prio become False
        .up_limit(up_limit)
        .dl_limit(dl_limit)
        .category(category)
        .sequential_download(True)
        .first_last_piece_prio(True)
        .auto_tmm(False)
        .include_file(sample.data, f"{sample.name}.torrent")
        .build()
    )
    await one_moment()

    torrents = await client.torrents.info(hashes=(sample.hash,))
    assert len(torrents) == 1

    # verify torrent is correctly added
    info = torrents[0]
    assert info is not None, torrents
    assert info.name == "add-renamed"
    assert info.hash == sample.hash
    assert info.state in {TorrentState.CHECKING_RESUME_DATA, TorrentState.PAUSED_DL}
    assert info.up_limit == up_limit
    assert info.dl_limit == dl_limit
    assert info.seq_dl
    assert info.f_l_piece_prio
    assert not info.auto_tmm
    assert info.category == category
    assert info.save_path.replace("\\", "/").rstrip("/") == savepath
    assert abs((info.added_on - now).total_seconds()) <= 10, (info.added_on, now)

    # ratioLimit, seedingTimeLimit requires API v2.8.1
    await client.torrents.delete((sample.hash,), True)


@pytest.mark.asyncio
async def test_add_mixed(client: APIClient):
    """Add torrents with mixed of data and urls"""
    sample_data1 = make_torrent_single("add_mixed_data1")
    sample_data2 = make_torrent_single("add_mixed_data2")
    sample_magnet1 = make_torrent_single("add_mixed_magnet1")
    sample_magnet2 = make_torrent_single("add_mixed_magnet2")
    sample_hash1 = make_torrent_single("add_mixed_hash1")
    sample_hash2 = make_torrent_single("add_mixed_hash2")

    await client.torrents.add(
        AddFormBuilder.with_client(client)
        .paused(True)
        .include_file(sample_data1.data, "data1.torrent")
        .include_url(sample_magnet1.magnet)
        .include_url(sample_hash1.hash)
        .include_file(sample_data2.data, "data2.torrent")
        .include_url(sample_magnet2.magnet)
        .include_url(sample_hash2.hash)
        .build()
    )
    await one_moment()

    hashes = (
        sample_data1.hash,
        sample_data2.hash,
        sample_magnet1.hash,
        sample_magnet2.hash,
        sample_hash1.hash,
        sample_hash2.hash,
    )
    torrents = await client.torrents.info(hashes=hashes)
    assert len(torrents) == len(hashes)

    await client.torrents.delete(hashes, True)


def test_add_builder():
    builder = AddFormBuilder()
    builder_copy = copy.copy(builder)

    assert builder == builder_copy

    builder2 = builder.include_url("0" * 40)

    assert builder != builder2


@pytest.mark.asyncio
async def test_add_error(client: APIClient):
    with pytest.raises(exc.AddTorrentError):
        await client.torrents.add(AddFormBuilder.with_client(client).build())


@pytest.mark.asyncio
async def test_delete_error(client: APIClient):
    with pytest.raises(ValueError):
        await client.torrents.delete("0" * 40, True)


@pytest.mark.asyncio
async def test_torrent_metadata(client: APIClient):
    sample = make_torrent_single("torrent_metadata")
    info_hash = sample.hash
    now = datetime.datetime.now()

    async with temporary_torrents(client, sample):
        # torrents.info()
        torrents = await client.torrents.info(hashes=(info_hash,))
        assert isinstance(torrents, list)
        assert len(torrents) == 1

        info = torrents[0]
        assert isinstance(torrents[0], TorrentInfo)
        assert isinstance(repr(info), str)
        assert abs((info.added_on - now).total_seconds()) <= 10

        # torrents.properties()
        props = await client.torrents.properties(info_hash)
        assert isinstance(props, TorrentProperties)
        assert isinstance(repr(props), str)
        assert abs((props.addition_date - now).total_seconds()) <= 10

        # torrents.webseeds()
        webseeds = await client.torrents.webseeds(info_hash)
        assert isinstance(webseeds, list)
        assert len(webseeds) == 0

        # torrents.piece_states
        piece_states = await client.torrents.piece_states(info_hash)
        assert isinstance(piece_states, list)
        assert len(piece_states)
        assert all(s == PieceState.UNAVAILABLE for s in piece_states)

        # torrents.piece_hashes
        piece_hashes = await client.torrents.piece_hashes(info_hash)
        assert isinstance(piece_hashes, list)
        assert len(piece_hashes)
        assert len(piece_hashes) == len(piece_states)
        assert all(isinstance(s, str) and len(s) == 40 for s in piece_hashes)


@pytest.mark.asyncio
async def test_manipulation(client: APIClient):
    sample = make_torrent_single("manipulation")
    info_hash = sample.hash
    hashes = (info_hash,)

    async with temporary_torrents(client, sample):
        await client.torrents.rename(sample.hash, "manipulation2")
        await one_moment()

        info = (await client.torrents.info(hashes=hashes))[0]
        assert info.name == "manipulation2"

        # torrents.resume
        async def tell_resumed():
            torrents = await client.torrents.info(filter=InfoFilter.RESUMED, hashes=hashes)
            return any(s.hash == info_hash for s in torrents)

        async def tell_paused():
            torrents = await client.torrents.info(filter=InfoFilter.PAUSED, hashes=hashes)
            return any(s.hash == info_hash for s in torrents)

        await client.torrents.resume(hashes)
        assert await busy_wait_for(tell_resumed, 5), await client.torrents.info()

        await client.torrents.set_force_start(hashes, True)
        await one_moment()

        await client.torrents.set_super_seeding(hashes, True)
        await one_moment()

        info = (await client.torrents.info(hashes=hashes))[0]
        assert info.state == TorrentState.FORCED_DL
        assert not info.super_seeding, "incomplete torrent cannot be super seeding"

        # torrents.reannounce
        await client.torrents.reannounce(hashes)
        await one_moment()

        # torrents.add_peers
        await client.torrents.add_peers(hashes, ("127.0.0.2:8080", "127.0.0.3:8080"))
        await one_moment()

        # torrents.pause
        await client.torrents.pause(hashes)
        assert await busy_wait_for(tell_paused, 5), await client.torrents.info()

        new_save_path = f"{info.save_path}/magic-directory"
        await client.torrents.set_location(hashes, new_save_path)
        await one_moment()

        info = (await client.torrents.info(hashes=hashes))[0]
        assert info.save_path.rstrip("/").endswith("magic-directory")

        # torrents.recheck
        await client.torrents.recheck(hashes)
        await one_moment()


@pytest.mark.asyncio
async def test_rename_file(client: APIClient):
    assert client.api_version is not None
    if client.api_version >= (2, 7, 0):
        pytest.skip("rename file is changed after API v2.8.0 or client v4.3.3")

    sample = make_torrent_files("rename_file")

    async with temporary_torrents(client, sample):
        files = await client.torrents.files(sample.hash)
        assert len(files) == 5
        assert files[3].name == "rename_file/files/03.txt"

        await client.torrents.rename_file(sample.hash, 3, "rename_file_3")
        await one_moment(1)

        async def get_third_filename():
            files = await client.torrents.files(sample.hash)
            return files[3].name

        await busy_assert_eq("rename_file/files/rename_file_3", get_third_filename)


@pytest.mark.asyncio
async def test_torrent_auto_tmm(client: APIClient):
    sample = make_torrent_single("torrent_auto_tmm")
    hashes = (sample.hash,)

    async with temporary_torrents(client, sample) as torrents:
        info = torrents[0]
        auto_tmm = info.auto_tmm
        await client.torrents.set_auto_management(hashes, not auto_tmm)
        await one_moment()

        info = (await client.torrents.info(hashes=hashes))[0]
        assert auto_tmm != info.auto_tmm


@pytest.mark.asyncio
async def test_torrent_seq_dl(client: APIClient):
    sample = make_torrent_single("torrent_seq_dl")
    hashes = (sample.hash,)

    async with temporary_torrents(client, sample) as torrents:
        info = torrents[0]
        seq_dl = info.seq_dl
        await client.torrents.toggle_sequential_download(hashes)
        await one_moment()

        info = (await client.torrents.info(hashes=hashes))[0]
        assert seq_dl != info.seq_dl

        await client.torrents.set_sequential_download(hashes, seq_dl)
        await one_moment()

        info = (await client.torrents.info(hashes=hashes))[0]
        assert seq_dl == info.seq_dl

        await client.torrents.set_sequential_download(hashes, seq_dl)
        await one_moment()

        info = (await client.torrents.info(hashes=hashes))[0]
        assert seq_dl == info.seq_dl


@pytest.mark.asyncio
async def test_torrent_flp_prio(client: APIClient):
    sample = make_torrent_single("torrent_flp_prio")
    hashes = (sample.hash,)

    async with temporary_torrents(client, sample) as torrents:
        info = torrents[0]
        flp_prio = info.f_l_piece_prio
        await client.torrents.toggle_first_last_piece_prio(hashes)
        await one_moment()

        info = (await client.torrents.info(hashes=hashes))[0]
        assert flp_prio != info.f_l_piece_prio

        await client.torrents.set_first_last_piece_prio(hashes, flp_prio)
        await one_moment()

        info = (await client.torrents.info(hashes=hashes))[0]
        assert flp_prio == info.f_l_piece_prio

        await client.torrents.set_first_last_piece_prio(hashes, flp_prio)
        await one_moment()

        info = (await client.torrents.info(hashes=hashes))[0]
        assert flp_prio == info.f_l_piece_prio


@pytest.mark.asyncio
async def test_limits(client: APIClient):
    dl_limit = 111
    up_limit = 222
    ratio_limit = 2
    stl = datetime.timedelta(days=1)

    sample = make_torrent_single("limits")
    info_hash = sample.hash

    async with temporary_torrents(client, sample):
        # set dl_limit, up_limit, share_limits
        await client.torrents.set_download_limit((info_hash,), dl_limit)
        await client.torrents.set_upload_limit((info_hash,), up_limit)
        await client.torrents.set_share_limits((info_hash,), ratio_limit, stl)
        await one_moment()

        # check limits
        info = (await client.torrents.info(hashes=(info_hash,)))[0]
        assert info.dl_limit == dl_limit
        assert info.up_limit == up_limit
        assert info.ratio_limit == ratio_limit
        assert info.seeding_time_limit == stl

        # torrents.download_limit()
        download_limits = await client.torrents.download_limit((info_hash,))
        assert info_hash in download_limits
        assert download_limits[info_hash] == dl_limit

        # torrents.upload_limit()
        upload_limits = await client.torrents.upload_limit((info_hash,))
        assert info_hash in upload_limits
        assert upload_limits[info_hash] == up_limit


@pytest.mark.asyncio
async def test_trackers(client: APIClient):
    tracker = f"{client.base_url}/missing/tracker"
    tracker2 = f"{client.base_url}/missing/tracker2"
    tracker3 = f"{client.base_url}/missing/tracker3"

    sample = make_torrent_single("trackers")
    info_hash = sample.hash

    async with temporary_torrents(client, sample):
        # torrents.trackers
        trackers = await client.torrents.trackers(info_hash)
        assert isinstance(trackers, list)
        assert len(trackers) == 3
        assert all(s.is_special() for s in trackers)

        # torrents.add_trackers
        await client.torrents.add_trackers(info_hash, (tracker, tracker2))
        await one_moment()

        await client.torrents.edit_tracker(info_hash, tracker2, tracker3)
        await one_moment()

        await client.torrents.remove_trackers(info_hash, (tracker,))
        await one_moment()

        trackers = await client.torrents.trackers(info_hash)
        assert len(trackers) == 4
        assert any(s.url == tracker3 for s in trackers)


@pytest.mark.asyncio
async def test_queueing(client: APIClient):
    sample1 = make_torrent_single("queueing1")
    sample2 = make_torrent_single("queueing2")
    sample3 = make_torrent_single("queueing3")
    hashes = (sample1.hash, sample2.hash, sample3.hash)

    # make sure queueing is on or the following would fail
    await client.app.set_preferences(
        {
            "queueing_enabled": True,
        }
    )

    async with temporary_torrents(client, sample1, sample2, sample3):
        h1, h2, h3 = hashes

        async def queued_hashes():
            torrents = await client.torrents.info(hashes=hashes)
            torrents.sort(key=lambda s: s.priority)
            return [s.hash for s in torrents]

        await client.torrents.top_prio((h3,))
        await client.torrents.top_prio((h2,))
        await client.torrents.top_prio((h1,))
        # order: 1, 2, 3

        await busy_assert_eq([h1, h2, h3], queued_hashes, timeout=3)

        await client.torrents.increase_prio((h2,))
        # order: 2, 1, 3

        await client.torrents.decrease_prio((h1,))
        # order: 2, 3, 1

        await client.torrents.bottom_prio((h2,))
        # order: 3, 1, 2

        await busy_assert_eq([h3, h1, h2], queued_hashes, timeout=3)


@pytest.mark.asyncio
async def test_file_priorities(client: APIClient):
    sample = make_torrent_files("file_priorities")
    info_hash = sample.hash

    async def file_priorities():
        return [s.priority for s in await client.torrents.files(info_hash)]

    async with temporary_torrents(client, sample):
        assert len(await file_priorities()) == 5

        # libtorrent default priority is 4 which is invalid in qbittorrent
        # so set all to NORMAL first
        await client.torrents.file_prio(info_hash, range(5), FilePriority.NORMAL)
        await busy_assert_eq([FilePriority.NORMAL] * 5, file_priorities)

        # modify some of them
        await client.torrents.file_prio(info_hash, [0, 4], FilePriority.MAXIMAL)
        await busy_assert_eq(
            [
                FilePriority.MAXIMAL,
                FilePriority.NORMAL,
                FilePriority.NORMAL,
                FilePriority.NORMAL,
                FilePriority.MAXIMAL,
            ],
            file_priorities,
        )

        await client.torrents.file_prio(info_hash, [2], FilePriority.NO_DOWNLOAD)
        await busy_assert_eq(
            [
                FilePriority.MAXIMAL,
                FilePriority.NORMAL,
                FilePriority.NO_DOWNLOAD,
                FilePriority.NORMAL,
                FilePriority.MAXIMAL,
            ],
            file_priorities,
        )


@pytest.mark.asyncio
async def test_categories(client: APIClient):
    sample = make_torrent_single("categories")
    info_hash = sample.hash
    category_name = "category_name"
    category_path = "category_path"

    # Create category
    await client.torrents.create_category(category_name, category_path)
    await one_moment()

    # Get categories
    categories = await client.torrents.categories()
    assert isinstance(categories, dict)
    assert category_name in categories
    assert isinstance(categories[category_name], Category)
    assert categories[category_name].savePath == category_path

    # Edit category save path
    await client.torrents.edit_category(category_name, "")
    await one_moment()

    categories = await client.torrents.categories()
    assert categories[category_name].savePath == ""

    async with temporary_torrents(client, sample):
        await client.torrents.set_category((info_hash,), category_name)
        await one_moment()

        info = (await client.torrents.info(hashes=(info_hash,)))[0]
        assert info.category == category_name

    # Remove category
    await client.torrents.remove_categories((category_name,))
    await one_moment()

    categories = await client.torrents.categories()
    assert category_name not in categories


@pytest.mark.asyncio
async def test_tags(client: APIClient):
    sample = make_torrent_single("tags")
    info_hash = sample.hash

    async with temporary_torrents(client, sample):
        add_tags = ["dragon-fruits", "figs", "grapes"]
        create_tags = ["apples", "bananas", "cherries"]

        # add tags
        await client.torrents.add_tags((info_hash,), add_tags)
        await one_moment()

        # remove tags
        await client.torrents.remove_tags((info_hash,), ("figs",))
        await one_moment()

        # create tags
        await client.torrents.create_tags(create_tags)
        await one_moment()

        # delete tags
        await client.torrents.delete_tags(("bananas", "dragon-fruits"))
        await one_moment()

        # tags
        expected_tags = {"figs", "grapes", "apples", "cherries"}
        tags = await client.torrents.tags()
        assert isinstance(tags, list)
        assert set(tags) == expected_tags

        await client.torrents.delete_tags(sorted(expected_tags))
