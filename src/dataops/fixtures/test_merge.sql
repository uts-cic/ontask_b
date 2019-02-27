--
-- PostgreSQL database dump
--

-- Dumped from database version 10.4
-- Dumped by pg_dump version 10.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
-- SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: __ONTASK_WORKFLOW_TABLE_1; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."__ONTASK_WORKFLOW_TABLE_1" (
    key double precision,
    text1 text,
    text2 text,
    double1 double precision,
    double2 double precision,
    bool1 boolean,
    bool2 boolean,
    date1 timestamp without time zone,
    date2 timestamp without time zone
);


--
-- Data for Name: __ONTASK_WORKFLOW_TABLE_1; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public."__ONTASK_WORKFLOW_TABLE_1" (key, text1, text2, double1, double2, bool1, bool2, date1, date2) FROM stdin;
1	d1_t1_1	\N	111	\N	t	\N	2018-01-01 01:00:00	\N
2	d2_t1_2	\N	112	\N	f	\N	2018-01-01 02:00:00	\N
3	\N	d1_t2_3	\N	123	\N	f	\N	2018-01-02 03:00:00
4	\N	d1_t2_4	\N	124	\N	t	\N	2018-01-02 04:00:00
5	d1_t1_5	\N	115	\N	f	\N	2018-01-01 05:00:00	\N
6	d1_t1_6	\N	116	\N	t	\N	2018-01-01 06:00:00	\N
7	\N	d1_t2_7	\N	126	\N	t	\N	2018-01-02 07:00:00
8	\N	d1_t2_8	\N	127	\N	f	\N	2018-01-02 08:00:00
\.


--
-- PostgreSQL database dump complete
--

